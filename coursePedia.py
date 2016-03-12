#coding=utf-8

from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from pymongo import MongoClient
import json
from bson  import ObjectId
from flask import request
from flask import session
import pymongo

app = Flask(__name__)


@app.route('/schools')
# get all school info from db
def get_all_schools():
    client = MongoClient()
    db = client.courses
    cursor = db.schools.find()
    schs = []
    for s in cursor:
        schs.append({'id':s['id'], 'name':s['name']})
    return json.dumps(schs)


@app.route('/courses/<school_id>')
# get courses given the school id from db
def get_all_courses(school_id):
    client = MongoClient()
    db = client.courses
    cursor = db.courses.find({'schoolId': school_id})
    courses = []
    for c in cursor:
        courses.append({'name':c[u"课程名"], 'teacher': c[u"任课教师"], 'id': str(c['_id']),
                        'rating': 0 if c['rating_cnt'] == 0 else c['rating_sum'] / c['rating_cnt'],
                        'gradeType': c['gradeType']})
    courses.sort(key=lambda x: x['rating'], reverse=True)
    return json.dumps(courses)

@app.route('/requestPost/<course_id>/<user_id>')
# check whether the user has evaluated the course
def isEvaluated(course_id, user_id):
    client = MongoClient()
    db = client.courses
    cursor = db.posts.find({'course_id': course_id, 'user_id': user_id})
    if cursor.count() == 0:
        return "0"
    else:
        return "1"


@app.route('/requestVote/<user_id>/<post_id>')
#check whether the use has voted this post
def isVoted(user_id, post_id):
    client = MongoClient()
    db = client.courses
    cursor = db.votes.find({'user_id': user_id, 'post_id': post_id})
    if cursor.count() == 0:
        return "0"
    else:
        return "1"


@app.route('/saveVote', methods=['POST', 'GET'])
#save vote into db
def saveVote():
    if request.method == 'POST':
        user_id = request.form['user_id']
        post_id = request.form['post_id']
        #increment for the vote
        inc = int(request.form['inc'])
        print 'inc:', inc
        client = MongoClient()
        db = client.courses

        #check whether the user voted the post before, should at most one
        cursor = db.votes.find({'user_id': user_id, 'post_id': post_id})
        if cursor.count() == 0:
            #never voted
            #insert new vote
            db.votes.insert_one({'user_id': user_id, 'post_id': post_id, 'vote': inc})
        else:
            #update the existing vote
            for c in cursor:
                c['vote'] += inc
            db.votes.save(c)

        print inc
        #update votes for the post
        res = db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'votes': inc}}
        )
        return "1"


@app.route('/')
def show_courses():
    return render_template('show_courses.html')

#get course given the course id
#course_id should be unique
def get_course(course_id):
    client = MongoClient()
    db = client.courses
    cursor = db.courses.find({'_id': ObjectId(course_id)})
    # cursor = db.courses.find()
    print cursor.count()
    # for c in cursor:
    #     print c['_id']
    if cursor.count() != 1:
        # print course_id
        return None
    course = {'id': course_id, 'name': cursor[0][u"课程名"], 'teacher': cursor[0][u"任课教师"],
              'school': cursor[0][u"开课院系"], 'rating': 0 if cursor[0]['rating_cnt'] == 0 else cursor[0]['rating_sum'] / cursor[0]['rating_cnt'],
              'gradeType': cursor[0]['gradeType']}
    return course


#cal course rating given the course
def cal_rating(course):
    return 0 if course['rating_cnt'] == 0 else course['rating_sum'] / course['rating_cnt']



@app.route('/course/<course_id>')
def show_course(course_id):
    c = get_course(course_id)
    if c is None:
        return course_id
    return render_template('course.html', course=c)

#return user with the given email, should at most one
def find_user_with_email(email):
    client = MongoClient()
    db = client.courses
    cursor = db.users.find({'email': email})
    if cursor.count() == 0:
        return None
    return {'id': cursor[0]['_id'], 'email': cursor[0]['email'], 'password': cursor[0]['password'], 'alias': cursor[0]['alias']}

#return user with the given alias, should at most one
def find_user_with_alias(alias):
    client = MongoClient()
    db = client.courses
    cursor = db.users.find({'alias': alias})
    if cursor.count() == 0:
        return None
    return {'id':cursor[0]['_id'], 'email': cursor[0]['email'], 'password': cursor[0]['password'], 'alias': cursor[0]['alias']}



#create new user given the email and password
#return the objectId
def create_new_user(email, password, alias):
    client = MongoClient()
    db = client.courses
    return db.users.insert_one({'email': email, 'password': password, 'alias': alias}).inserted_id


#check the user info trying to login
def validateLoginInfo(email, password):
    user = find_user_with_email(email)
    return user is not None and user['password'] == password



# user request for signup new user
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        alias = request.form['alias']
        email = request.form['email']
        password = request.form['password']
        user = find_user_with_alias(alias)
        if user is not None:
            return json.dumps(["0", "该昵称已被使用"])
        user = find_user_with_email(email)
        if user is not None:
            return json.dumps(["0", "该邮箱已被使用"])
        user_id = str(create_new_user(email, password, alias))
        return json.dumps(["1", user_id, alias])

# user request for login
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = find_user_with_email(email)
        if user is not None and user['password'] == password:
            session['user_id'] = str(user['id'])
            return json.dumps(["1", str(user['id']), user['alias']])
        else:
            return json.dumps(["0"])

# user request for save post
@app.route('/savePost', methods=['POST', 'GET'])
def savePost():
    if request.method == 'POST':
        course_id = request.form['course_id']
        user_id = request.form['user_id']
        rating = float(request.form['rating'])
        content= request.form['content']
        client = MongoClient()
        db = client.courses
        res = db.posts.insert_one({'course_id': course_id, 'user_id': user_id, 'rating': rating, 'content': content, 'votes': 0})
        #update rating statics in course
        db.courses.update_one(
            {'_id': ObjectId(course_id)},
            {'$inc': {'rating_cnt': 1, 'rating_sum': rating}}
        )
        return json.dumps(["1", str(res.inserted_id)])
    return json.dumps(["0"])


#load all posts given the course_id
@app.route('/posts/<course_id>')
def loadAllPosts(course_id):
    client = MongoClient()
    db = client.courses
    cursor = db.posts.find({'course_id': course_id}).sort([("votes", pymongo.DESCENDING)])
    posts = []
    current_user_id = session['user_id']
    for c in cursor:
        post_id = str(c['_id'])
        cursor1 = db.votes.find({'user_id': current_user_id, 'post_id': post_id})
        currentUserVote = 0
        if cursor1.count() > 0:
            currentUserVote = cursor1[0]['vote']
        #user id of the poster
        user_id = c['user_id']
        aliasCursor = db.users.find({'_id': ObjectId(user_id)})
        alias = aliasCursor[0]['alias']
        posts.append({'id': post_id, 'user_id': c['user_id'], 'rating': c['rating'],
                      'content': c['content'], 'votes': c['votes'], 'currentUserVote': currentUserVote,
                      'userAlias': alias})
    return json.dumps(posts)

#set secret key
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == '__main__':
    app.debug = True
    # app.config['SERVER_NAME'] = 'app'
    app.run()