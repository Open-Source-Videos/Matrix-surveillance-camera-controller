# Communications reference

All messages have 3 parameters, type, content, requestor_id. By default requestor_id will be "0" and represents a message for all remote clients

## Types of messages FROM camera hub

### cam-config: 
content = dict, or object structure. The keys are the camera number, the values are the camera names.

Example:
    
`{"type":"cam-config", "content":{"1":"Camera1", "2":"Cam 2 name"}, "requestor_id":"0"}`

### error: 
content = string. This notifies all clients that there was an error serving up a request by a remote client.

Example:

`{"type" : "error", "content" : "File Upload Failed", "requestor_id":"0"}`

### snapshot-send: 
content = string - is the camera ID for the snapshot whose picture is taken, comma separated is the time at which the image is taken. This is the reply to a snapshot request.

Example:

`{"type" : "snapshot-send", "content" : "1,2022-05-06T13:04:04.482374", "requestor_id":"client_that_requested"}`

### video-send: 
content = string - contains the path / name of the video, followed by the ISO datetime that the video was recorded. This is sent to the client that requested it.

Example:

`{"type" : "video-send", "content" : "/var/lib/motioneye/Camrea1/02-05-2022/15-25-30.mp4,2022-02-05T15:25:30", "requestor_id":"client_that_requested"}`

### thumbnail: 
content = string. The content is the path / name of the thumbnail and video, followed by the ISO datetime that the video was recorded. Upon a motion detection event a thumbnail is uploaded to everyone when the video has been recorded.

Example:

`{"type" : "thumbnail", "content" : "/var/lib/motioneye/Camera1/02-05-2022/15-25-30.mp4.thumb, 2022-02-05T15:25:30", "requestor_id":"0"}`


### thumb-reply: 
content = string. When a thumbnail for a particular video is requested this reply is the thumbnail.

Example:

`{"type" : "thumb-reply", "content" : "/var/lib/motioneye/Camera1/02-05-2022/15-25-30.mp4.thumb, 2022-02-05T15:25:30", "requestor_id":"client_that_requested"}`



### list-recording-reply:
content = string. Upon user request to list out stored video thumbnails from a specified date range, the output will be a json containing the 'date_range' which was provided in the original request, and an array of the pairs of file paths to the found video thumbnails, and their time stamps. These thumbnail file paths can then be used to request the videos.

Example:

`{"type" : "list-recording-reply", "content" : "{'date_range': '2022-05-06T00:00:01, 2022-05-06T14:10:00', 'recordings': [['/var/lib/motioneye/Camera1/2022-05-06/00-58-33.mp4.thumb', '2022-05-06T00:58:33'], ['/var/lib/motioneye/Camera1/2022-05-06/12-31-45.mp4.thumb', '2022-05-06T12:31:45'], ['/var/lib/motioneye/Camera1/2022-05-06/01-01-20.mp4.thumb', '2022-05-06T01:01:20']]}", "requestor_id" : "my_client_name"}`


## Types of messages TO camera hub

### snapshot: 
content = string or integer. This requests a screenshot from the camera hub. Content must specify the camera number whose snapshot is requested.
Example:

`{"type" : "snapshot", "content" : "1", "requestor_id":"my_client_name"}`

Expected reply is a screenshot sent to the client specified in the requestor_id field, or an error.

### video-request: 
content = string. The content string should be the fully qualified name for the thumbnail as provided when thumbnail was sent.

Example:

`{"type" : "video-request", "content" : "/var/lib/motioneye/Camrea1/02-05-2021/15-25-30.mp4.thumb", "requestor_id":"my_client_name"}`

Expected reply is a video directed to the client specified in the requestor_id field that matches the thumbnail or an error.


### thumb-request:
content = string. The content string should be the fully qualified name for a thumbnail which is requested.

Example:

`{"type" : "thumb-request", "content" : "/var/lib/motioneye/Camrea1/02-05-2021/15-25-30.mp4.thumb", "requestor_id":"my_client_name"}`

Expected reply is the thumbnail file directed to the client specified in the requestor_id field that matches the thumbnail or an error. 

### record-video:
Note on this, it triggers a simulated motion detection for the specified duration in seconds. So it'll appear to everyone as if its a motion detection event video. Maximum duration is 300 seconds, and a minimum of 1 second.

content = string. The content needs to contain the camera and the duration comma separated. like "1,20" will be camera 1, 20 seconds.

`{"type" : "record-video", "content" : "1,20", "requestor_id":"0"}`

Expected reply is a motion detection event after the specified duration.

### cam-config-request: 
content = string. Content can be null. This will just request to that camera hub send out an updated list of cameras.
Example:

`{"type" : "cam-config-request", "content" : "", "requestor_id":"my_client_name"}`

Expected reply is a cam-config message.

### list-recordings:
content = string. String should be two dates. Start Datetime, followed by end datetime, 24 hour clock. 'stardatetime, enddatetime' in the format 'YYYY-MM-DDTHH:MM:SS,YYYY-MM-DDTHH:MM:SS'.
The following example will request a list of recordings between April 27th 2022, at 10:30:00 AM, and April 28th 2022, at 2:45:30 PM.

`{"type" : "list-recordings", "content" : "2022-04-27T10:30:00, 2022-04-28T14:45:30", "requestor_id":"my_client_name"}`

Expected reply is a list of all saved recordings for that time duration.