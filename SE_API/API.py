
__author__ = 'sagi'
import json
from GithubAPI.GithubAPI import GitHubAPI_Keys

from google.appengine.ext import db
import requests
import uuid

from flask import Flask, request, render_template, redirect, abort, Response

from flask.ext.github import GitHub
from flask.ext.cors import CORS, cross_origin
from flask.ext.autodoc import Autodoc

# DB Models
from models.User import User
from models.Course import Course
from models.Project import Project
from models.Campus import Campus

#Validation Utils Libs
from SE_API.Validation_Utils import *
from SE_API.Respones_Utils import *




app = Flask(__name__, static_folder='../templates')

githubKeys = GitHubAPI_Keys()

app.config['GITHUB_CLIENT_ID'] = githubKeys.getId()
app.config['GITHUB_CLIENT_SECRET'] = githubKeys.getSecret()

github = GitHub(app)
cross = CORS(app)
auto = Autodoc(app)

@app.errorhandler(404)
def page_not_found(e):
    return app.send_static_file('views/404/index.html')

@app.route('/')
def wellcomePage():
    return app.send_static_file('index.html')

@app.route('/api/validation/confirm/<string:validation_token>', methods=["GET"])
@auto.doc()
def confirm_user_to_campus(validation_token):
    """
    <span class="card-title">This Function is will Activate a user and add tha campus to it</span>
    <br>
    <b>Route Parameters</b><br>
        - validation_token: 'seToken|email_suffix'
    <br>
    <br>
    <b>Payload</b><br>
     - NONE
    <br>
    <br>
    <b>Response</b>
    <br>
    200 - redirect to home + new cookie
    <br>
    403 - Invalid Token
    """
    #TODO
    token = str(validation_token).split('|')[0]
    email_sufix = '@'+str(validation_token).split('|')[1]

    user = get_user_by_token(token)

    if user is None:
        return forbidden('Forbidden: invalid Token')
    else:
        campus = get_campus_by_suffix(email_sufix)
        if campus is None:
            return bad_request('Bad Request: Email Suffix ' + email_sufix + ' Not Found')
    user.isFirstLogin = False
    user.seToken = str(uuid.uuid4())
    if str(campus.key().id()) not in user.campuses_id_list:
        user.campuses_id_list.append(str(campus.key().id()))
    db.put(user)
    return cookieMonster(user.seToken)



@app.route('/api/validation/sendmail/<string:token>', methods=['POST'])
@auto.doc()
def send_activation(token):
    """
    <span class="card-title">This Method Will Send An Email To The User - To Confirm his Account</span>
    <br>
    <b>Route Parameters</b><br>
        - token: 'seToken'<br>
    <br>
    <b>Payload</b><br>
     - JSON object <i>Example</i>
     <br>
     <code>{email: 'academic@email.ac.com'}</code>
    <br>
    <br>
    <b>Response</b>
    <br>
    200 - Email Sent - No Response<br>
    400 - Bad Request<br>
    403 - Invalid Token<br>
    """
    if not request.data:
        return Response(response=json.dumps({'message': 'Bad Request'}),
                        status=400,
                        mimetype="application/json")
    payload = json.loads(request.data)
    if not is_user_token_valid(token):
        return Response(response=json.dumps({'message': 'Not A Valid Token!'}),
                        status=403,
                        mimetype="application/json")
    query = User.all()
    query.filter('seToken =', token)
    for u in query.run(limit=1):
        try:
            send_validation_email(token=token, name=u.username, email=payload["email"])
        except Exception:
            return Response(response=json.dumps({'message': 'Bad Request'}),
                     status=400,
                     mimetype="application/json")

        return Response(status=200)

@app.route('/api/help')
def documentation():
    return auto.html()

@app.route('/home')
def returnHome():
    try:
        return app.send_static_file('views/index.html')
    except Exception:
        abort(404)



@app.route('/api/getUserByToken/<string:token>', methods=["GET"])
@auto.doc()
def getUserByToken(token):
    '''
    <span class="card-title">This Function is will Activate a user and add tha campus to it</span>
    <br>
    <b>Route Parameters</b><br>
        - validation_token: 'seToken|email_suffix'
    <br>
    <br>
    <b>Payload</b><br>
     - NONE
    <br>
    <br>
    <b>Response</b>
    <br>
    200 - JSON Example:<br>
    <code>
        {<br>
        'username' : 'github_username',<br>
        'name' : 'Bob Dylan',<br>
        'email' : 'email@domain.com',<br>
        'isLecturer' : true,<br>
        'seToken' : 'dds2d-sfvvsf-qqq-fdf33-sfaa',<br>
        'avatar_url' : 'http://location.domain.com/image.jpg',<br>
        'isFirstLogin' : false,<br>
        'campuses_id_list': ['22314','243512',...,'356'],<br>
        'classes_id_list': ['22314','243512',...,'356']<br>
        }
    </code>
    <br>
    403 - Invalid Token
    '''
    query = User.all()
    query.filter("seToken = ", token)

    for u in query.run(limit=5):
        return Response(response=u.to_JSON(),
                        status=201,
                        mimetype="application/json")  # Real response!

    return Response(response=json.dumps({'message' : 'No User Found'}),
                    status=400,
                    mimetype="application/json")



@app.route('/githubOAuth')
@cross_origin('*')
@github.authorized_handler
def oauth(oauth_token):
    if oauth_token is None:
        return render_template("index.html", messages={'error': 'OAuth Fail'})
    try:
        response = requests.get("https://api.github.com/user?access_token=" + oauth_token)
        user_data = json.loads(response.content)
        response = requests.get("https://api.github.com/user/emails?access_token=" + oauth_token)
        userEmails = json.loads(response.content)
    except Exception:
        return "<h1>Max Retries connection To Github</h1><p>github has aborted connection due to to many retries. you need to wait</p>"

    resault = User.all()
    resault.filter("username =", str(user_data["login"]))

    print user_data["login"]

    for u in resault.run():
        print "Exists!!!"
        u.seToken = str(uuid.uuid4())
        u.accessToken = oauth_token
        u.put()
        return cookieMonster(u.seToken)

    tempName = ";"

    if user_data["email"] == "":
        for email in userEmails:
            if email["primary"] and email["verified"]:
                tempEmail = email["email"]
    else:
        tempEmail = user_data["email"]

    user = User(username=user_data["login"], name=tempName, avatar_url=user_data["avatar_url"], email=tempEmail, isLecturer=False, accessToken=oauth_token, seToken=str(uuid.uuid4()))
    db.put(user)
    db.save
    return cookieMonster(user.seToken)


@app.route('/api/Campuses/create/<string:token>', methods=['POST'])
@auto.doc()
def create_campus(token):
    """
    <span class="card-title">This call will create a new campus in the DB</span>
    <br>
    <b>Route Parameters</b><br>
        - seToken: 'seToken'
    <br>
    <br>
    <b>Payload</b><br>
     - JSON Object, Example: <br>
     {<br>
     'title': 'Campus name',<br>
     'email_ending': '@campus.ac.com',<br>
     'avatar_url': 'http://location.domain.com/image.jpg'<br>
    }<br>
    <br>
    <br>
    <b>Response</b>
    <br>
    201 - Created
    <br>
    403 - Invalid Token/Forbidden
    """
    print "1\n"
    if not request.data:
        return Response(response=json.dumps({'message': 'Bad Request0'}),
                        status=400,
                        mimetype="application/json")
    payload = json.loads(request.data)
    if not is_lecturer(token):  #todo: change to lecturer id
        return Response(response=json.dumps({'message': 'Invalid token or not a lecturer!'}),
                        status=403,
                        mimetype="application/json")

    user = get_user_by_token(token)

    #todo: check legality

    try:
        campus = Campus(title=payload['title'], email_ending=payload['email_ending'], master_user_id=user.key().id(), avatar_url=payload['avatar_url'])
    except Exception:
        return Response(response=json.dumps({'message': 'Bad Request1'}),
                        status=400,
                        mimetype="application/json")

    db.put(campus)
    db.save
    return Response(response=json.dumps(campus.to_JSON()),
                                status=201,
                                mimetype="application/json")




@app.route('/api/Campuses/<string:token>', methods=['GET'])
@auto.doc()
def get_campuses(token):
    """
    <span class="card-title">This Call will return an array of all Campuses available</span>
    <br>
    <b>Route Parameters</b><br>
        - seToken: 'seToken'
    <br>
    <br>
    <b>Payload</b><br>
     - NONE <br>
    <br>
    <br>
    <b>Response</b>
    <br>
    200 - JSON Array, Example:<br>
    [<br>
    {
                'title': 'JCE',<br>
                'email_ending': '@post.jce.ac.il',<br>
                'master_user_id': 123453433341, (User that created the campus)<br>
                'avatar_url': 'http://some.domain.com/imagefile.jpg'<br>
    },<br>
    ....<br>
    {<br>
    ...<br>
    }req<br>
    ]<br>
    <br>
    403 - Invalid Token<br>
    500 - Server Error
    """
    if is_user_token_valid(token):
        arr = []
        query = Campus.all()
        for c in query.run():
            arr.append(dict(json.loads(c.to_JSON())))
        print arr
        if len(arr) != 0:
            return Response(response=json.dumps(arr),
                            status=200,
                            mimetype="application/json")
        else:
            return Response(response=[],
                            status=200,
                            mimetype="application/json")
    else:
        return Response(response=json.dumps({'message': 'Invalid Token'}),
                        status=403,
                        mimetype="application/json")



@app.route('/login')
@cross_origin('*')
def login():
    return github.authorize()




def cookieMonster(uid):
    redirect_to_home = redirect('/home')
    response = app.make_response(redirect_to_home )
    response.set_cookie('com.sehub.www',value=uid)
    return response
