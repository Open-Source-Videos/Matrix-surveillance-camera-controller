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
content = string - may be blank. This is the reply to a snapshot request.

Example:

`{"type" : "snapshot-send", "content" : "", "requestor_id":"client_that_requested"}`

### video-send: 
content = string - contains the path / name of the video. This is sent to the client that requested it.

Example:

`{"type" : "video-send", "content" : "/var/lib/motioneye/Camrea1/02-05-2021/15-25-30.mp4", "requestor_id":"client_that_requested"}`

### thumbnail: 
content = string. Upon a motion detection event a thumbnail is uploaded to everyone when the video has been recorded.

Example:

`{"type" : "thumbnail", "content" : "/var/lib/motioneye/Camera1/02-05-2021/15-25-30.mp4.thumb", "requestor_id":"0"}`


### list-video-response:
content = string. Upon user request to list out stored video thumbnails from a specified storage location, the output will be a json containing the file path to the found video thumbnail.

Example:

`{"type" : "list-video-response", "content" : "/var/lib/motioneye/Camera1/2022-04-03/16-15-27.mp4.thumb", "requestor_id" : "0"}`


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

### record-video:
Note on this, it triggers a simulated motion detection for the specified duration in seconds. So it'll appear to everyone as if its a motion detection event video. Maximum duration is 300 seconds, and a minimum of 1 second.

content = string. The content needs to contain the camera and the duration comma separated. like "1,20" will be camera 1, 20 seconds.

`{"type" : "record-video", "content" : "1,20", "requestor_id":"0"}`

Expected reply is a motion detection event after the specified duration.

### list-video:

content = string. The content string is broken into the camera parameter and the date parameter. For example, "1,2022-04-08" will refer to files from the camera identified as "camera 1" that were taken on the date 2022-04-08.

Example:

`{"type" : "list-video", "content" : "Camera1,2022-04-08", "requestor_id" : "0"}`

Expected reply is a series of file paths that point to stored video thumbnail files located in the specified camera and date directories.

### cam-config-request: 
content = string. Content can be null. This will just request to that camera hub send out an updated list of cameras.
Example:

`{"type" : "cam-config-request", "content" : "", "requestor_id":"my_client_name"}`

Expected reply is a cam-config message.
