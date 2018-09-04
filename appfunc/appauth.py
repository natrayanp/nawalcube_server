from . import bp_appfunc
from flask import redirect, request,make_response, jsonify
#from flask_cors import CORS, cross_origin
from nawalcube.common import dbfunc as db
from nawalcube.common import error_logics as errhand
from nawalcube.common import jwtfuncs as jwtf
from datetime import datetime
import os
import hashlib
import hmac
import binascii
import jwt


@bp_appfunc.route("/appauth",methods=["GET","POST","OPTIONS"])
def appauth():
    # This function is called to authenticate app
    # Input --> 2
    #       1) in payload authtoken, apiid , apikey & redirecturi are mandatory
    #       2) in header countryid and entityid
    # Output --> 2
    #       1) success : {'passtkn': password token} 
    #       2) error: {"errormessage": response["usrmsg"]}
    # {value: 'I', viewValue: 'Investor'}, 
    # {value: 'D', viewValue: 'Distributor (MFD)'}, 
    # {value: 'A', viewValue: 'Advisor (RIA)'},
    # {value: 'P', viewValue: 'Portfolio Tools'},
    # {value: 'T', viewValue: 'Trusted Apps'}
    if request.method=="OPTIONS":
        print("inside login options")
        return "inside login options"

    elif request.method=="POST":
        payload = request.get_json()
        print(payload)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        #userid = jwtf.decodetoken(request, needtkn = False)
        entityid = request.headers.get("entityid", None)
        cntryid = request.headers.get("countryid", None)
        
        criteria_json = {
            # "userid"   : userid,
            "entityid" : entityid,
            "cntryid"  : cntryid,
            "payload" : payload
        }
        
        res_to_send, response = app_appauth(criteria_json)

        if res_to_send == "success":
            response1 = response["result_data"]
        else:
            response1 = {"errormessage": response["usrmsg"]}

        resps = make_response(jsonify(response1), 200)
        return resps

def app_appauth(criteria_json):
    print("inside appauth function")
    s = 0
    f = None
    t = None #message to front end
    response = None
    res_to_send = 'fail'
    payload = criteria_json.get("payload",None)
    
    print(s)
    if s <= 0:
        if criteria_json.get("entityid", None) != None:
            entityid = criteria_json['entityid']
        else:
            entityid = None
            s, f, t= errhand.get_status(s, 100, f, "entity id not provided", t, "yes")

        if criteria_json.get("cntryid", None) != None:
            cntryid = criteria_json['cntryid']
        else:
            cntryid = None
            s, f, t= errhand.get_status(s, 100, f, "cntry code is not provided", t, "yes")       
        
        if payload == None:
            s, f, t= errhand.get_status(s, 100, f, "App data not sent.  Please try again", t, "yes")
        else:
            if payload.get("userauthtkn", None) != None:
                userauthtkn = criteria_json['userauthtkn']
            else:
                userauthtkn = None
                s, f, t= errhand.get_status(s, 100, f, "User login success authtkn not provided", t, "yes")

            if payload.get("appid", None) != None:
                appid = criteria_json['appid']
            else:
                appid = None
                s, f, t= errhand.get_status(s, 100, f, "app id not provided", t, "yes")

            if payload.get("appkey", None) != None:
                appkey = criteria_json['appkey']
            else:
                appkey = None
                s, f, t= errhand.get_status(s, 100, f, "appkey is not provided", t, "yes")

            if payload.get("redirecturi", None) != None:
                redirecturi = criteria_json['redirecturi']
            else:
                redirecturi = None
                s, f, t= errhand.get_status(s, 100, f, "redirecturi is not provided", t, "yes")
                # update or create are the values

            
    
    print(userauthtkn,appid,redirecturi,appkey,entityid,cntryid)

    if s <= 0:
        con, cur, s1, f1 = db.mydbopncon()
        s, f, t = errhand.get_status(s, s1, f, f1, t, "no")
        s1, f1 = 0, None
        print("DB connection established", s,f,t)
    

    if s <= 0:
        command = cur.mogrify("""
                                SELECT json_agg(a) FROM (
                                SELECT *
                                FROM ncusr.appdetail
                                WHERE delflg != 'Y' AND expirydate >= CURRENT_DATE
                                AND appid = %s AND appkey = %s AND redirecturi = %s
                                AND entityid = %s AND countryid = %s
                                ) as a
                            """,(appid, appkey, redirecturi, entityid, cntryid,) )
        print(command)
        cur, s1, f1 = db.mydbfunc(con,cur,command)
        s, f, t = errhand.get_status(s, s1, f, f1, t, "no")
        s1, f1 = 0, None
        print('----------------')
        print(s)
        print(f)
        print('----------------')
        if s > 0:
            s, f, t = errhand.get_status(s, 200, f, "App Name data fetch failed with DB error", t, "no")
    print(s,f)
    
    app_db_rec = None
    if s <= 0:
        app_db_rec = cur.fetchall()[0][0]
        print(app_db_rec)
    
        if len(app_db_rec) > 0:
            s, f, t= errhand.get_status(s, 100, f, "Unable to locate the app id", t, "yes")            
        else:
            app_db_rec = app_db_rec[0]
            print("App id identified successfully")
            pass            
    
    print(s,f)

    appuserid = app_db_rec.get("appuserid", None)
    if s <= 0:
        command = cur.mogrify("""
                            SELECT json_agg(a) FROM (
                            SELECT *
                            FROM ncusr.userauth
                            WHERE tknexpiry >= CURRENT_TIMESTAMP
                            AND userid = %s AND userauthtkn = %s
                            AND entityid = %s AND countryid = %s
                            ) as a
                        """,(appuserid, userauthtkn, entityid, cntryid,) )
        print(command)
        cur, s1, f1 = db.mydbfunc(con,cur,command)
        s, f, t = errhand.get_status(s, s1, f, f1, t, "no")
        s1, f1 = 0, None
        print('----------------')
        print(s)
        print(f)
        print('----------------')
        if s > 0:
            s, f, t = errhand.get_status(s, 200, f, "User authtoke fetch failed with DB error", t, "no")
    print(s,f)

    usr_db_rec = None
    if s <= 0:
        usr_db_rec = cur.fetchall()[0][0]
        print(usr_db_rec)
    
        if len(usr_db_rec) > 0:
            s, f, t= errhand.get_status(s, 100, f, "Unable to locate the user auth details OR Token expired", t, "yes")            
        else:
            usr_db_rec = usr_db_rec[0]
            print("User auth token validated successfully")
            pass            
    
    #We are ready to generate API pass token
    print(s,f)
    i = 0
    cur_time = datetime.now().strftime('%Y%m%d%H%M%S')
    passtknset = False
    pass_tkn = None

    while i < 50:
        r = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(6))
        pass_tkn = create_signature("md5", "nirunidhapasstkn" + r, userauthtkn + cur_time, appuserid + appid)

        command = cur.mogrify("""
                                SELECT count(1)
                                FROM ncusr.appdetail
                                WHERE pass_tkn = %s
                            """,(pass_tkn,) )
        print(command)
        cur, s1, f1 = db.mydbfunc(con,cur,command)
        s, f, t = errhand.get_status(s, s1, f, f1, t, "no")
        s1, f1 = 0, None
        print('----------------')
        print(s)
        print(f)
        print('----------------')
        if s > 0:
            s, f, t = errhand.get_status(s, 200, f, "Password token data fetch failed with DB error", t, "no")
        print(s,f)

        if s <= 0:
            db_rec = cur.fetchall()[0][0]
            print(db_rec)
        
            if db_rec > 0:
                s, f, t= errhand.get_status(s, 100, f, "Pass token Already exists. Retrying time: " + i, t, "no")
                i = i + 1
                continue
            else:
                print("Pass code is unique.  Generation task completed")
                passtknset = True
                break
        else:
            # Some error occured, so no point looping
            passtknset = False
            break
    
    print(s,f, t)

    appusrtype = app_db_rec.get("appusertype", None)
    if appusrtype == None:
        s, f, t= errhand.get_status(s, 200, f, "app user type is not known", t, "yes")

    if s <= 0 and passtknset:
        s1, f1 = db.mydbbegin(con, cur)
        print(s1,f1)

        s, f, t= errhand.get_status(s, s1, f, f1, t, "no")
        s1, f1 = 0, None

        if s <= 0:
            passexpiry = get_expiry_time(appusrtype)

            command = cur.mogrify("""
                        UPDATE ncusr.appdetail SET passwordtkn = %s, passwordtknexpiry = %(timestamp)s, lmtime = CURRENT_TIMESTAMP
                        WHERE  appid =%s AND userid = %s AND entityid = %s AND countryid = %s;
                        """,(pass_tkn, {'timestamp': passexpiry.datetime.strptime(t,'%d-%m-%YT%H:%M:%S'), appid, userid, entityid, cntryid,))
            print(command)

            cur, s1, f1 = db.mydbfunc(con,cur,command)
            s, f, t= errhand.get_status(s, s1, f, f1, t, "no")
            s1, f1 = 0, None

            if s > 0:
                s, f, t= errhand.get_status(s, 200, f, "passtoken update failed", t, "no")

            print('Insert or update is successful')
    
        if s <= 0:
            con.commit()
    
    if s <= 0:
        data_for_jwt = { 
                            "exp": passexpiry.datetime.strftime('%d%m%Y%H%M%S'),
                            "passtkn": pass_tkn,
                            "ei" : entityid, 
                            "ci" : cntryid
                        }
        natjwt = jwtf.generatejwt(data_for_jwt)
        
    if s > 0:
        res_to_send = 'fail'
        result_date = []
        response = {
            'result_data' : result_date,
            'status': res_to_send,
            'status_code': s,
            'usrmsg': errhand.error_msg_reporting(s, t)
            }
    else:
        res_to_send = 'success'
        result_date = natjwt
        response = {
                    'result_data' : result_date,
                    'status': res_to_send,
                    'status_code': 0,
                    'usrmsg': "Token generation successful"
        }

    print(res_to_send, response)
    
    return (res_to_send, response)


def create_signature(hastype, more_key_str, key, message):
  d = more_key_str + key
  b = d.encode()

  message = message.encode()
  if hastype == "md5":
    return hmac.new(b, message, hashlib.md5).hexdigest()
  elif hastype == "sha256":
    return hmac.new(b, message, hashlib.sha256).hexdigest()


def get_expiry_time(ut) -> datetime:
    # Set the app token expiry based on the user type
    # I - Investor - 1 day
    # D - MFD  - 1 hour
    # A - RIA  - 1 hour
    # P - Portfolio tool - 1 hour
    # T - Trusted app - 1 hour
    ct = datetime.now().strftime('%Y%m%d%H%M%S')

    if ut == 'I':
        et = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif ut == 'D':
        et = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif ut == 'A':
        et = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif ut == 'P':
        et = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif ut == 'T':
        reference_time = datetime.datetime.now()
        et = reference_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1,microseconds=-1)       
        #Example et value 2018-09-04 23:59:59.999999
    return et