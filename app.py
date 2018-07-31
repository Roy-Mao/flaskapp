from flask import Flask, render_template, request, redirect, session
from aip import AipFace
from werkzeug.utils import secure_filename
import boto3, os, botocore, pdb, sys, base64, requests, ssl, json
#from config import S3_KEY, S3_SECRET, S3_BUCKET, APP_ID, API_KEY, SECRET_KEY


app = Flask(__name__)
#app.debug = True
app.config['SECRET_KEY'] = os.environ['APP_SECRET_KEY']

s3 = boto3.client(
    "s3",
    aws_access_key_id = os.environ['S3_KEY'],
    aws_secret_access_key =  os.environ['S3_SECRET']
)

APP_ID = os.environ['APP_ID']
API_KEY =  os.environ['API_KEY']
SECRET_KEY = os.environ['SECRET_KEY']
client = AipFace(APP_ID, API_KEY, SECRET_KEY)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=["GET"])
def hello_wold():
    return render_template('hello.html', user_image = "https://s3-ap-northeast-1.amazonaws.com/hakone930313/money_logo.png", analyze_str = "no content")



@app.route('/', methods=["POST"])
def upload_file():
    if "user_file" not in request.files:
        return "No user_file key in request.files"
    file = request.files["user_file"]
    if file.filename == "":
        return "Please select a file"
    if file and allowed_file(file.filename):
        file.filename = secure_filename(file.filename)
        full_filename = upload_file_to_s3(file, os.environ['S3_BUCKET'])
        session["image_path"] = full_filename
        return render_template("hello.html", user_image = full_filename, analyze_str = "no result")
    else:
        return redirect("/")

@app.route('/analyze', methods=["GET"])
def face_scan():
    img_url = session.get('image_path')
    imageType = "BASE64"
    img_base64 = base64.b64encode(requests.get(img_url).content)
    image = img_base64.decode()

    options = {
        "face_field":  "age,gender,glasses,beauty,expression,face_shape",
        "max_face_num": 5,
        "face_type": "CERT"
    }
    try:
        result = client.detect(image, imageType, options)
        response = json.dumps(result)
        response_js = json.loads(response)
        recognizable = False if response_js["result"] is None else True
        if recognizable:
            result      = response_js["result"]["face_list"][0]
            age         = result["age"]
            beauty      = result["beauty"]
            sex         = "女性" if result["gender"]["type"]== "female" else "男性"
            glasses     = result["glasses"]["type"]
            expression  = result["expression"]["type"]
            face_shape  = result["face_shape"]["type"]
            analyze_str = "あなたは：%d歳の%sでしょう, 顔の採点は %.2f 点です！表情: %s\n" %(age, sex, beauty, expression)
            analyze_str += "メガネをかけますか？答えは: " + glasses + " 顔の形：" + face_shape + "\n\n"
        else:
            analyze_str = 'この写真に対する分析データがないです！人の写真ではないはずと思ったんだよ!\n\n'
    except:
        e = sys.exc_info()[0]
        print ( "Unexpected Error: %s" % e )
        analyze_str = "Unexpected Error: %s" % e
    return render_template("hello.html", user_image = img_url, analyze_str = analyze_str)


def upload_file_to_s3(file, bucket_name, acl="public-read"):
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )
    except Exception as e:
        print("Something Happend: ", e)
        return e
    return "{}{}".format(os.environ['S3_LOCATION'], file.filename)
