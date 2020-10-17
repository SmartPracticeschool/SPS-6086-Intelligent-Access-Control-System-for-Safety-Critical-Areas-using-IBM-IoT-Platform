import json
from watson_developer_cloud import VisualRecognitionV3
import cv2
import os
import sys
import ibm_boto3
from ibm_botocore.client import Config
from ibm_botocore.exceptions import ClientError
import ibm_s3transfer.manager
import random
import datetime
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

import ibmiotf.application
import ibmiotf.device

from cloudant.client import Cloudant
from cloudant.error import CloudantException 
from cloudant.result import Result, ResultByKey

isFace = False
allok = False

authenticator = IAMAuthenticator('xIXUTpjZVGjozSwbSCoQh90saoL3Tc9Hbeioh14xgF-V')
text_to_speech = TextToSpeechV1(
    authenticator=authenticator
)

organization = "s2da29"
deviceType = "door"
deviceId = "1234"
authMethod = "token"
authToken = "v8*G94@)&_HpN9MO*B"

client = Cloudant("ac8f17de-ac32-409c-9d5f-bacafa0c8e1b-bluemix", "0c31b8f2408bd1335d7c68f0346cd67024d697a0c4af797ecf0a1ef2353e420e", url="https://ac8f17de-ac32-409c-9d5f-bacafa0c8e1b-bluemix:0c31b8f2408bd1335d7c68f0346cd67024d697a0c4af797ecf0a1ef2353e420e@ac8f17de-ac32-409c-9d5f-bacafa0c8e1b-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()
database_name = "door"
bucket_name = "14bucket14"
picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")
picname=picname+".jpg"
pic=datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")

COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # example: https://s3.us-south.cloud-object-storage.appdomain.cloud
COS_API_KEY_ID = "7aLsGcOhlWRwMnKduYo6NTT5yeurbKqQoXlSfzCA8Jip" # example: xxxd12V2QHXbjaM99G9tWyYDgF_0gYdlQ8aWALIQxXx4
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_SERVICE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/d07c3e24d97345b4b79f48540b41a703:d9f6827e-3d49-4e3f-852b-0b5215af0a4c::" # example: crn:v1:bluemix:public:cloud-object-storage:global:a/xx999cd94a0dda86fd8eff3191349999:9999b05b-x999-4917-xxxx-9d5b326a1111::
COS_STORAGE_CLASS = "smart tier" # example: us-south-standard

try:
	deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
	deviceCli = ibmiotf.device.Client(deviceOptions)
	
except Exception as e:
	print("Caught exception connecting device: %s" % str(e))
	sys.exit()

deviceCli.connect()

cos_cli = ibm_boto3.client("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_SERVICE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

def myCommandCallback(cmd):
        print("Door outhorization message received: %s" % cmd.data)
        print(cmd.data['command'])       

        if(cmd.data['command']=="open"):
            	print("Authorization Success. Please enter.")
               
        if(cmd.data['command']=="close"):
            	print("Authorization Failed. Please try again.")


def captureImage():
	vidObj = cv2.VideoCapture(0,cv2.CAP_DSHOW)
	_, image = vidObj.read() 
	cv2.imwrite(picname , image) 
	

def checkFace():
	face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
	img = cv2.imread(picname)
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	faces = face_cascade.detectMultiScale(gray, 1.1, 4)
	if len(faces):
		global isFace
		isFace = True
			

def securityCheck():
	isHelmet = False
	isShoes = False
	visual_recognition = VisualRecognitionV3(
    	'2018-03-19',
    	iam_apikey='ErHI67WnIe7UQ8-Aq5AbBc_8qX03LkXcLPnJe0NS1fyG')

	with open(picname, 'rb') as images_file:
	    cl = visual_recognition.classify(
	       images_file,
	       threshold='0.6',
	    classifier_ids='default').get_result()

	file1 = open("MyFile_1.txt","w+")
	for x in cl["images"][0]["classifiers"][0]["classes"]:
		print(x["class"])
		file1.write(x["class"])
		file1.write("\n")
	file1.close()

	with open("MyFile_1.txt") as file:
		for line in file:
			if 'helmet' in line:
				isHelmet = True
			elif 'headdress' in line:
				isHelmet = True
			elif 'hard hat' in line:
				isHelmet = True
			elif 'shoes' in line:
				isShoes = True
			elif 'shoe' in line:
				isShoes = True
			elif 'footwear	' in line:
				isShoes = True

	if isHelmet == True and isShoes == True:
		global allok
		allok = True

def uploadtodatabase():
	my_database = client.create_database(database_name)
	uploadImage(bucket_name, picname, "C:/python/python37/"+pic+".jpg")
	if my_database.exists():
            print("'{database_name}' successfully created.")
            json_document = {
                    "_id": pic,
                    "link":COS_ENDPOINT+"/14bucket14/"+picname
                    }
            new_document = my_database.create_document(json_document)
            if new_document.exists():
                print("Document '{new_document}' successfully created.")
    
def uploadImage(bucket_name, item_name, file_path):
    print("Starting large file upload for {0} to bucket: {1}".format(item_name, bucket_name))

    # set the chunk size to 5 MB
    part_size = 1024 * 1024 * 5

    # set threadhold to 5 MB
    file_threshold = 1024 * 1024 * 5

    # set the transfer threshold and chunk size in config settings
    transfer_config = ibm_boto3.s3.transfer.TransferConfig(
        multipart_threshold=file_threshold,
        multipart_chunksize=part_size
    )

    # create transfer manager
    transfer_mgr = ibm_boto3.s3.transfer.TransferManager(cos_cli, config=transfer_config)

    try:
        # initiate file upload
        future = transfer_mgr.upload(file_path, bucket_name, item_name)

        # wait for upload to complete
        future.result()

        print ("Large file upload complete!")
    except Exception as e:
        print("Unable to complete large file upload: {0}".format(e))
    finally:
        transfer_mgr.shutdown()


def generateSpeech():
	from ibm_watson import TextToSpeechV1
	from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

	authenticator = IAMAuthenticator('xIXUTpjZVGjozSwbSCoQh90saoL3Tc9Hbeioh14xgF-V')
	text_to_speech = TextToSpeechV1(
	    authenticator=authenticator
	)

	text_to_speech.set_service_url('https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/da501530-b8eb-4927-86e7-4d1197b00567')

	if allok == True:
		with open('allok.wav', 'wb') as audio_file:
		    audio_file.write(
		        text_to_speech.synthesize(
		            'Safety check successful. Please enter.',
		            voice='en-US_AllisonVoice',
		            accept='audio/wav'        
		        ).get_result().content)	
	
	elif allok == False:
		with open('notok.wav', 'wb') as audio_file:
		    audio_file.write(
		        text_to_speech.synthesize(
		            'Safety check failed. Please retry.',
		            voice='en-US_AllisonVoice',
		            accept='audio/wav'        
		        ).get_result().content)	


def deviceControl():
	def myOnPublishCallback():
		print ("Published data to IBM Watson")
	data = {'person' : allok}
	success = deviceCli.publishEvent("Data", "json", data, qos=0, on_publish=myOnPublishCallback)
	if not (success):
		print("Not connected to IoTF")
		time.sleep(1)
	deviceCli.commandCallback = myCommandCallback

def log_error(msg):
    print("UNKNOWN ERROR: {0}\n".format(msg))

def end():
	print("end")


def main():
	try:
		while True:
			captureImage()
			checkFace()
			if isFace == True:
				securityCheck()
				generateSpeech()
				uploadtodatabase()
				deviceControl()
			


			Key=cv2.waitKey(1)
			if Key==ord('q'):
				vidObj.release()
				cv2.destroyAllWindows()
				break
		end()
	except Exception as e:
		log_error("Main Program Error: {0}".format(e))

if __name__ == "__main__":
    main()
