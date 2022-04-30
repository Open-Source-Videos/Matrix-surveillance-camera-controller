import asyncio
import configparser
from email import message
from imp import get_magic
import json
import os
import sys
import time
from datetime import datetime, date, time
import getpass
from PIL import Image
import aiofiles.os
import magic
import logging

#File watcher, async
from watchdog.observers import Observer

#MATRIX NIO SDK classes
from nio import AsyncClient, AsyncClientConfig, LoginResponse, UploadResponse, RoomResolveAliasError, RoomMessageText, RoomMessage


#Configuration setup
config = configparser.ConfigParser()
try:
    config.read('/var/lib/ossc_client/config.cfg')
except Exception as e:
    print("CONFIG FILE NOT FOUND!")
    print(e)
    sys.exit(1)

CRED_FILE = config['FILES']['cred_file']
STORE_PATH = config['FILES']['store_path']
LOG_PATH = config['FILES']['log_path']
RECORDING_PATH = config['FILES']['recording_path']
CAM_CONFIG_PATH = config['FILES']['cam_config_path']

#Global variable to keep track of cameras.
CAMERAS = {}

try:
    #Setup for logging
    logging.basicConfig(filename=(LOG_PATH + "ossc_client.log"),level=logging.INFO, format='%(asctime)s - %(message)s') #Config without an output file
    logger = logging.getLogger("ossc_client_log")
except Exception as e:
    print("Logging directory not found. Please check config, and or create the correct directory. Exiting")
    print(e)
    sys.exit(1)


#Async IO watchdog wrapper
class AIOWatchdogWrapper(object):
    def __init__(self, path='.', event_handler=None):
        self._observer = Observer()
        self.eventhandler = event_handler
        self._observer.schedule(self.eventhandler, path, True)
    def start(self):
        self._observer.start()
    def stop(self):
        self._observer.stop()
        self._observer.join()

#Event Hander for file monitor.
class EventHandler():
    def __init__(self, client, room_id):
        self.loop = asyncio.get_event_loop()
        self.future = asyncio.create_task
        self.client = client
        self.room_id = room_id
        self.methods = {
            "moved": self.on_moved,
            "modified": self.on_modified,
            "deleted": self.on_deleted,
            "created": self.on_created,
            "closed": self.on_closed,
        }
    def dispatch(self, event):
        self.loop.call_soon_threadsafe(self.future, self.methods[event.event_type](event))

    #Events for files being modified. Specifically camera config files
    async def on_modified(self, event):
        # Config file update on camera
        if str(event.src_path).endswith('.conf') and str(event.src_path).startswith(CAM_CONFIG_PATH + "camera-"):
            global CAMERAS
            # New camera added. Notify clients that
            i = 0
            #Try for 10 seconds to wait for the file to be completely written
            while not magic.from_file(event.src_path, mime=True).startswith("text/") and i < 10:
                await asyncio.sleep(1)
                i += 1
            if i < 10:
                with open(event.src_path, "r") as f:
                    for line in f:
                        if line.startswith('camera_name'):
                            cam_name = line.replace('camera_name ', '').strip()
                            camnum = str(event.src_path).replace(CAM_CONFIG_PATH + "camera-", '').replace('.conf','')
                            CAMERAS[str(camnum)] = cam_name
                            logger.info("Camera config modified: " + camnum + " - " + cam_name)
                #Update cam configs
                await send_cam_configs(self.client, self.room_id)

    #On file delete check to see if its a camera configuration file, and handle the update
    async def on_deleted(self, event):
        if str(event.src_path).endswith('.conf') and str(event.src_path).startswith(CAM_CONFIG_PATH):
            global CAMERAS
            # Camera removed from config. Notify remote client.
            camnum = str(event.src_path).replace(CAM_CONFIG_PATH + "camera-", '')
            camnum = camnum.replace('.conf', '')
            try:
                del CAMERAS[camnum]
            except Exception as e:
                logger.info("Failed to remove camera config: " + str(e))

            logger.info("Camera config modified: " + camnum + " removed")
            #Update cam configs
            await send_cam_configs(self.client, self.room_id)
        pass
    
    #File move events... none
    async def on_moved(self, event):
        #Currently no configs for on moved files
        pass

    #Files closed. Not used
    async def on_closed(self, event):
        pass

    #File creation events. Thumbnails mostly, but also cameras being added.
    async def on_created(self, event):
        logger.info(event)
        if str(event.src_path).endswith('.thumb'):
            logger.info("New motion detect video. Uploading thumbnail")
            try:
                i = 0
                #Try for 10 seconds to wait for the file to be completely written
                while not magic.from_file(event.src_path, mime=True).startswith("image/") and i < 10:
                    await asyncio.sleep(1)
                    i += 1
                result = await send_image(self.client, self.room_id, str(event.src_path), requestor_id="0", msg_type="thumbnail", text=str(event.src_path))
                if result != "success":
                    msg = '{"type" : "error", "content" :"' + result + '", "requestor_id" : "0"}'
                    await send_message(self.client, self.room_id, msg)
            except Exception as error:
                logger.info("Motion detect image thumb send fail" + str(error))
        elif str(event.src_path).endswith('.conf') and str(event.src_path).startswith(CAM_CONFIG_PATH + "camera-"):
            global CAMERAS
            # New camera added. Notify clients that
            i = 0
            #Try for 10 seconds to wait for the file to be completely written
            while not magic.from_file(event.src_path, mime=True).startswith("text/") and i < 10:
                await asyncio.sleep(1)
                i += 1
            if i < 10:
                with open(event.src_path, "r") as f:
                    #Look for the line with the camera name in it.
                    for line in f:
                        if line.startswith('camera_name'):
                            cam_name = line.replace('camera_name ', '').strip()
                            camnum = str(event.src_path).replace(CAM_CONFIG_PATH + "camera-", '').replace('.conf','')
                            CAMERAS[str(camnum)] = cam_name
                            #Write the new cam config to the config file
                            logger.info("New camera added: " + camnum + " - " + cam_name)
                await send_cam_configs(self.client, self.room_id)


#Take a snapshot and upload it to the client, room. Camera number required.
async def snapshot_upload(client, room_id, camera, requestor_id = 0):
    impath = RECORDING_PATH + "snapshot.jpg"
    command = "curl -m 10 -o " + impath + " http://localhost:8765/picture/" + str(camera) + "/current"
    try:
        os.system(command)
        #Try for 10 seconds to wait for the file to be completely written
        i = 0
        while not magic.from_file(impath, mime=True).startswith("image/") and i < 10:
            await asyncio.sleep(1)
            i += 1

        logger.info("Snapshot should be taken. Attempting to upload")
        result = await send_image(client, room_id, impath, requestor_id = str(requestor_id), msg_type="snapshot-send", text=str(camera))
        if result != "success":
            msg = '{"type" : "error", "content" :"' + result + '", "requestor_id":"' + str(requestor_id) + '"}'
            await send_message(client, room_id, msg)
    except Exception as e:
        logger.info("Failed to take and upload snapshot: " + str(e))
    

#Creates file monitor, and event handler, then waits. Watches cam files, and config files.
async def file_monitor(path, client, room_id, cam_path):
    handler = EventHandler(client, room_id)
    filemonitor = AIOWatchdogWrapper(path, event_handler=handler)
    filemonitor.start()
    configmonitor = AIOWatchdogWrapper(cam_path, event_handler=handler)
    configmonitor.start()
    logger.info("Starting File Monitor")
    try:
        while True:
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        filemonitor.stop()


#Dumps matrix config to disk
def write_details_to_disk(resp: LoginResponse, homeserver, room_id) -> None:
    # open the config file in write-mode
    with open(STORE_PATH + CRED_FILE, "w") as f:
        # write the login details to disk
        json.dump(
            {
                "homeserver": homeserver,  # e.g. "https://matrix.example.org"
                "user_id": resp.user_id,  # e.g. "@user:example.org"
                "device_id": resp.device_id,  # device ID, 10 uppercase letters
                "access_token": resp.access_token,  # cryptogr. access token
                "room_id": room_id,
            },
            f
        )

#Formats a camera configuration send event, and sends it.
async def send_cam_configs(client, room_id):
    msg = '{"type" : "cam-config", "content" : "' + str(CAMERAS) + '", "requestor_id" : "0"}'
    await send_message(client, room_id, msg)

#Finds all camera configuration files, and then extracts numbers and names
async def read_cam_configs():

    #Gets list of files in the config directory
    files = os.listdir(CAM_CONFIG_PATH)

    cameras_new = {}
    for f in files:
        if f.startswith('camera-') and f.endswith('.conf'):
            with open(CAM_CONFIG_PATH + f, "r") as c:
                for line in c:
                    if line.startswith('camera_name'):
                        cam_name = line.replace('camera_name ', '').strip()
                        camnum = f.replace("camera-", '').replace('.conf','')
                        cameras_new[str(camnum)] = cam_name
                        #Write the new cam config to the config file
                        logger.info("New camera added: " + camnum + " - " + cam_name)
    
    global CAMERAS
    CAMERAS = cameras_new

# Basic Message send to room.
async def send_message(client, room_id, message_text):
    try:
        if client.should_upload_keys:
            await client.keys_upload()
    except Exception as e:
        logger.info("Problem synching keys: " + str(e))

    content = {"msgtype": "m.text", "body": message_text}
    try:
        await client.room_send(
            room_id,
            message_type="m.room.message",
            content=content,
            ignore_unverified_devices=True,
        )
        logger.info("Message send success")
    except Exception as e:
        logger.info("Failed to send message: " + str(e))


# If the room given could be an alias try to resolve it into a room ID - Unused. Private rooms don't use aliases
async def room_id_from_alias(client, alias) -> str:
    result = await client.room_resolve_alias(alias)
    if isinstance(result, RoomResolveAliasError):
        print("Failed to resolve alias")
    else:
        return result.room_id


#Basically just checks if the first digit is a # -- Unused
def alias_check(room_id) -> bool:
    if room_id[0] == "#":
        return True
    return False


#Send Image File To Room
async def send_image(client, room_id, image, requestor_id = "0", msg_type = "blank", text = ""):
    #Adding support for custom text in image send
    if text == "":
        text = image

    try:
        if client.should_upload_keys:
            await client.keys_upload()
    except Exception as e:
        logger.info("Problem synching keys: " + str(e))

    #Checks to see if the file is an image format
    mime_type = magic.from_file(image, mime=True) 
    if not mime_type.startswith("image/"):
        logger.info("Failed to send image thumb. Mime type problem: " + str(mime_type))
        return "Unable to upload image for one of the following reasons: File doesn't exist, camera is off, another reason"

    im = Image.open(image)
    (width, height) = im.size  # im.size returns (width,height) tuple

    # first do an upload of image, then send URI of upload to room
    file_stat = await aiofiles.os.stat(image)
    async with aiofiles.open(image, "r+b") as f:
        resp, decrypt_keys = await client.upload(
            f,
            content_type=mime_type,  # image/jpeg
            filename=os.path.basename(image),
            filesize=file_stat.st_size,
            encrypt=True  # Always encrypt
        )
    if (isinstance(resp, UploadResponse)):
        logger.info("Image was uploaded successfully to server. ")
    else:
        logger.info(f"Failed to upload image. Failure response: {resp}")
        return "Failed to upload file"

    msg = '{"type":"' + msg_type + '", "content" : "' + text + '", "requestor_id":"' + requestor_id + '"}'

    # Now that the image has been uploaded, we need to message the room with this uploaded file.
    content = {
        "body": msg,
        "info": {
            "size": file_stat.st_size,
            "mimetype": mime_type,
            "thumbnail_info": None,  # This image is the thumbnail!
            "w": width,  # width in pixel
            "h": height,  # height in pixel
            "thumbnail_url": None,  # This image is the thumbnail!
        },
        "msgtype": "m.image",
        "file": {
            "url": resp.content_uri,
            "key": decrypt_keys["key"],
            "iv": decrypt_keys["iv"],
            "hashes": decrypt_keys["hashes"],
            "v": decrypt_keys["v"],
        },
    }

    try:
        await client.room_send(
            room_id,
            message_type="m.room.message",
            content=content,
            ignore_unverified_devices=True,
        )
        logger.info("Image send successful")
    except Exception as e:
        logger.info("Image send failure: " + str(e))
        return "Image send of file failed."

    return "success"


def get_motion_config_port():
    try:
        with open(CAM_CONFIG_PATH + "motioneye.conf") as f:
            for line in f:
                if line.startswith("motion_control_port"):
                    port = int(line.replace("motion_control_port ", "").strip())
    except Exception as e:
        logger.info(e)

    if isinstance(port, int):
        return str(port)
    return "fail"


async def record_video(client, room_id, duration=10, cam_id="1"):

    port = get_motion_config_port()
    logger.info("port: " + port)
    if port == "fail":
        err = '{"type" : "error", "content" : "Unable to find motion config port. Cannot trigger recording manually.", "requestor_id":"0"}'
        send_message(client, room_id, err)
    else:
        command = 'curl "http://localhost:' + port + '/' + cam_id + '/config/set?emulate_motion=1"'
        try:
            logger.info("Triggering simulated motion for " + str(duration) + " seconds")
            os.system(command)
            await asyncio.sleep(duration)
            command = 'curl "http://localhost:' + port + '/' + cam_id + '/config/set?emulate_motion=0"'
            os.system(command)
            logger.info("Simulated motion ended.")
        except Exception as e:
            logger.info(e) 
    return


#Send Video File to room.
async def send_video(client, room_id, video, msg_type="blank", requestor_id="0"):
    try:
        if client.should_upload_keys:
            await client.keys_upload()
    except Exception as e:
        logger.info("Problem synching keys: " + str(e))

    #Make sure file is video type
    mime_type = magic.from_file(video, mime=True) 
    if not mime_type.startswith("video/"):
        logger.info("Drop message because file does not have a video mime type.")
        return "Failed to send, bad file or file type"

    # first do an upload of the video, then send URI of upload to room
    file_stat = await aiofiles.os.stat(video)
    async with aiofiles.open(video, "r+b") as f:
        resp, decrypt_keys = await client.upload(
            f,
            content_type=mime_type,
            filename=os.path.basename(video),
            filesize=file_stat.st_size,
            encrypt=True  # Always encrypt
        )

    # Check response
    if (isinstance(resp, UploadResponse)):
        logger.info("Video send success: " + video)
    else:
        logger.info("Video send fail: " + str(resp))
        return "Video send of file " + video + "failed."

    # Now that the video has been uploaded, we need to message the room with this uploaded file.
    msg = '{"type":"' + msg_type + '", "content" : "' + os.path.basename(video) + '", "requestor_id":"' + requestor_id + '"}'

    #Build content package for message
    content = {
        "body": msg,
        "info": {"size": file_stat.st_size, "mimetype": mime_type},
        "msgtype":"m.video",
        "file": {
            "url": resp.content_uri,
            "key": decrypt_keys["key"],
            "iv": decrypt_keys["iv"],
            "hashes": decrypt_keys["hashes"],
            "v": decrypt_keys["v"],
        },
    }

    #Send video message
    try:
        await client.room_send(
            room_id,
            message_type="m.room.message",
            content=content,
            ignore_unverified_devices=True,
        )
        logger.info("Video send success: " + video)
    except Exception as e:
        logger.info("Video send fail: " + str(e))
        return "Video send of file " + video + "failed."
    return "success"

#List video thumbnails of a specified directory in the chat room.
async def list_recordings(client, room_id, date_range, files_in_range, msg_type = "list-video-response", requestor_id = "0"):
    try:
        for file in files_in_range:
            msg = '{"type" : "' + msg_type + '", "content" : "' + file + '", "requestor_id" : "' + requestor_id + '"}' #Construct json formatted message
            await send_message(client, room_id, msg) #Send complete message to the chat room
    except Exception as e:
        logger.info(e)


#Callbacks list for matrix listening client.
class Callback():
    def __init__(self, client, room_id) -> None:
        self.client = client
        self.room_id = room_id

    #Function that checks for received message types, and executes requests
    async def message_receive_callback(self, room, event) -> None:
        if(isinstance(event, RoomMessageText)) :
            logger.info(f"Event Received: {event}")

            #attempt to parse messages
            try:
                #Load in data as JSON
                message_data = json.loads(event.body)
                logger.info("JSON: " + str(message_data))

                #Check type in message data
                #Snapshot indicates a request for a live picture from a camera.
                if message_data['type'] == "snapshot":
                    logger.info("Attempting to upload snapshot.")
                    await snapshot_upload(self.client, self.room_id, message_data['content'], requestor_id = message_data['requestor_id'])
                    logger.info("Snapshot taken, and uploaded for camera " + str(message_data.camera) + " - for - " + message_data['requestor_id'])
                
                #Video-request is an upload request for a video that matches a supplied thumbnail.
                if message_data['type'] == "video-request":
                    if message_data['content'].endswith('.thumb'):
                        logger.info("Attempting to upload video: " + message_data['content'][:-6])
                        result = await send_video(self.client, self.room_id, message_data['content'][:-6], msg_type="video-send", requestor_id = message_data['requestor_id'])
                        if result != 'success':
                            msg = '{"type" : "error", "content" : "' + result + '", "requestor_id" : "' + message_data['requestor_id'] + '"}'
                            await send_message(self.client, self.room_id, msg)
                    else:
                        logger.info("Improperly formatted command: " + message_data['content'])
                
                #Cam config request is a general get request for all cameras.
                if message_data['type'] == "cam-config-request":
                    await send_cam_configs(self.client, self.room_id)

                #Record request.
                if message_data['type'] == "record-video":
                    try:
                        params = message_data['content'].strip().split(",")
                        cam = params[0]
                        dur = int(params[1])
                        logger.info("Video recording params: " + str(params))
                        if dur > 300:
                            dur = 300
                        elif dur < 1:
                            dur = 1
                        await record_video(self.client, self.room_id, dur, cam)
                    except Exception as e:
                        msg = '{"type" : "error", "content" : "Failed to trigger recording. Check request format", "requestor_id" : "' + message_data['requestor_id'] + '"}'
                        await send_message(self.client,self.room_id,msg)
                        logger.info("Failed to record video" + str(e))
                
                #List stored video thumbnails by date
                if message_data['type'] == "list-recordings":
                    try:
                        all_recordings = os.scandir(path = RECORDING_PATH) #Capture camera file paths

                        date_range = message_data['content'].strip().split(",") #Command parameters are comma-separated
                        startDate = datetime.fromisoformat(date_range[0]) #Convert to datetime
                        start = str(startDate) #Convert to string to allow split parsing
                        startSplit = start.split(" ") #Separate date and time
                        startDSplit = startSplit[0].split("-") #Parse out start date
                        dstart = date(int(startDSplit[0]),int(startDSplit[1]),int(startDSplit[2])) #Create date type from date numbers
                        endDate = datetime.fromisoformat(date_range[1]) #Convert to datetime
                        end = str(endDate) #Convert to string to allow split parsing
                        endSplit = end.split(" ") #Separate date and time
                        endDSplit = endSplit[0].split("-") #Parse out end date
                        dend = date(int(endDSplit[0]),int(endDSplit[1]),int(endDSplit[2])) #Create date type from date numbers

                        files_in_range = [] #Holds file paths in range
                        tformat = "%Y-%m-%d %H-%M-%S" #Sets datetime formatting
                        for cam in all_recordings: #Loop through camera directories
                            if(cam.name.startswith('Cam')): #Exclude snapshot
                                dates = os.scandir(cam.path) #Scan camera directory for date subdirectories
                                for d in dates: #Loop through date directories
                                    if(d.name != "lastsnap.jpg"): #Exclude lastsnap
                                        nameSplit = d.name.split("-") #Parse date name
                                        dname = date(int(nameSplit[0]), int(nameSplit[1]), int(nameSplit[2])) #Convert to date type
                                        if dname >= dstart and dname <= dend: #Compare dates
                                            camRecords = os.scandir(d.path) #Scan date directory for video recordings
                                            for f in camRecords: #Loop through date directories
                                                if f.name.endswith(".mp4.thumb"):
                                                    file = os.path.splitext(f.name) #Parse out .thumb extension
                                                    file = os.path.splitext(file[0]) #Parse out .mpt extension
                                                    dt = d.name + " " + file[0] #Construct datetime format
                                                    dtf = datetime.strptime(dt, tformat) #Convert to datetime.datetime type
                                                    if dtf >= startDate and dtf <= endDate: #Compare datetime of file
                                                        files_in_range.append(f.path) #A file that passes above checks must be within specified date range, add to list
                        await list_recordings(self.client, self.room_id, date_range, files_in_range, msg_type = "list-video-response", requestor_id = message_data['requestor_id'])

                    except Exception as e:
                        msg = '{"type" : "error", "content" : "Failed to list media directory contents. Check request format", "requestor_id" : "' + message_data['requestor_id'] + '"}'
                        await send_message(self.client, self.room_id, msg)
                        logger.info("Failed to list contents of media directory" + str(e))

                #Default other messages
                else:
                    logger.info("Message not for this client, or improperly formatted") 
            except Exception as e:
                logger.error("Action on incoming message error: " + str(e))
        return


#Listener creates the callbacks class and then says to wait forever.
async def start_listening(client, room_id) -> None:
    callback = Callback(client, room_id)
    client.add_event_callback(callback.message_receive_callback, (RoomMessageText, RoomMessage))
    while True:
        try:
            await client.sync_forever(timeout=30000, full_state=True)
        except Exception as e:
            logger.info("Client syncing failed. Will try again: " + str(e))



#Attempts to login, checks for config file, or prompts user for input.
async def login() -> AsyncClient:
    # If there are no previously-saved credentials, we'll use the password
    if not os.path.exists(STORE_PATH + CRED_FILE):
        logger.debug("First Run. Gathering info to log in to matrix")
        print("First time use. Did not find credential file. Asking for "
              "homeserver, user, and password to create credential file.")
        homeserver = "https://matrix.example.org"
        homeserver = input(f"Enter your homeserver URL: [{homeserver}] ")

        if not (homeserver.startswith("https://")
                or homeserver.startswith("http://")):
            homeserver = "https://" + homeserver

        user_id = "@user:example.org"
        user_id = input(f"Enter your full user ID: [{user_id}] ")

        device_name = "matrix-nio"
        device_name = input(f"Choose a name for this device: [{device_name}] ")

        client_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=True,
        )

        client = AsyncClient(
            homeserver,
            user_id,
            store_path=STORE_PATH,
            config=client_config,
        )
        pw = getpass.getpass()

        room_id = "!someroom:matrix.org"
        room_id = input(f"Enter room id for client: [{room_id}] ")

        logger.info("Attempting to log in...")
        logger.info("Homeserver: " + homeserver)
        logger.info("User ID: " + user_id)
        logger.info("Device Name: " + device_name)
        logger.info("Room ID: " + room_id)
        

        resp = await client.login(pw, device_name=device_name)

        # check that we logged in succesfully
        if (isinstance(resp, LoginResponse)):
            write_details_to_disk(resp, homeserver, room_id)
            logger.info("Login Successful. Credentials saved to disk.")
        else:
            logger.error(f"Failed to log in: {resp}")
            logger.error("Exiting...")
            print(f"homeserver = \"{homeserver}\"; user = \"{user_id}\"")
            print(f"Failed to log in: {resp}")
            sys.exit(1)

        print(
            "Logged in using a password successfully. Credentials were stored.",
        )

    # Otherwise the config file exists, so we'll use the stored credentials
    else:
        # open the file in read-only mode
        logger.info("Credentials file found. Restoring login")

        try:
            with open(STORE_PATH + CRED_FILE, "r") as f:

                #Setup config
                client_config = AsyncClientConfig(
                    max_limit_exceeded=0,
                    max_timeouts=0,
                    store_sync_tokens=True,
                    encryption_enabled=True,
                )
                config = json.load(f)

                #Create client set configs
                client = AsyncClient(
                    config['homeserver'],
                    store_path=STORE_PATH,
                    config=client_config)
                client.access_token = config['access_token']
                client.user_id = config['user_id']
                client.device_id = config['device_id']
                #Restore login info
                client.restore_login(
                    user_id=config['user_id'], device_id=config['device_id'], access_token=config['access_token'])
                room_id=config['room_id']
                logger.info("Login restored")
        except Exception as e:
            logger.error("Failed to restore login. Try deleting credentials file and logging back in: " + str(e))

    # Keys, syncing with server. Retry on failure
    while True:
        try:
            if client.should_upload_keys:
                await client.keys_upload()

            await client.sync(timeout=30000, full_state=True)
            logger.info("Client synch complete")
            return client, room_id
        except Exception as e:
            logger.error("Failed to sync with server. Waiting 20 seconds and trying again: " + str(e))
            await asyncio.sleep(20)


#Main shall log in, and then create the file listener task, and the matrix monitor task.
async def main():
    client, room_id = await login()
    #Update room with current cam configs
    await read_cam_configs()
    await send_cam_configs(client, room_id)

    logger.info("Login complete. Attempting to create event loop")
    loop = asyncio.get_event_loop()
    loop.create_task(listen(client, room_id))
    loop.create_task(start_monitor(client, room_id))
    logger.info("File monitor, message listener now running")

# Login and start listening
async def listen(client, room_id):
    await start_listening(client, room_id)

# Log in and start monitoring files
async def start_monitor(client, room_id):
    await file_monitor(RECORDING_PATH, client, room_id, CAM_CONFIG_PATH)

#Check if config file exists. If not, login for first time.
if not os.path.exists(STORE_PATH + CRED_FILE):
    asyncio.run(login())
    print("You may now run the program normally via the daemon, or restart it")
else:
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
