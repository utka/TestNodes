import mysql.connector
import random
import string

import datetime
import os
import sys


class DB ():

    def __init__(self, host, user, passwd, database):
        self.host=host
        self.user=user 
        self.passwd=passwd
        self.database=database
        self.mydb, self.mycursor = self.connect(host, user, passwd, database)

    def connect(self, host, user, passwd, database):
        mydb = mysql.connector.connect(
            host=host,
            user=user, 
            passwd=passwd, 
            database=database
        )
        mycursor = mydb.cursor(buffered=True, dictionary=True)
        return mydb, mycursor

    def execute_sql(self, sql, val):
        try:
            print(sql, val)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
        except mysql.connector.errors.DatabaseError as e:
            try:
                print(e)
                self.mycursor.close()
                self.mydb.close()
            except Exception as ee:
                print(ee)
            self.mydb, self.mycursor = self.connect(self.host, self.user, self.passwd, self.database)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
        except Exception as e:
            print(e)
            raise e
        return self.mycursor


class NayDuckDB (DB):
    def __init__(self):
        self.host=os.environ['NAYDUCK_DB_HOST']
        self.user=os.environ['NAYDUCK_DB_USER']
        self.passwd=os.environ['NAYDUCK_DB_PASSWD']
        self.database=os.environ['NAYDUCK_DB']
        super().__init__(self.host, self.user, self.passwd, self.database)
    
    def get_github_login(self, token):
        sql = "SELECT name FROM users WHERE code=%s"
        result = self.execute_sql(sql, (token,))
        login = result.fetchone()
        if login:
            return login['name']  
        return None

class MasterDB (DB):
    def __init__(self):
        self.host=os.environ['DB_HOST']
        self.user=os.environ['DB_USER'] 
        self.passwd=os.environ['DB_PASSWD']
        self.database=os.environ['DB']
        super().__init__(self.host, self.user, self.passwd, self.database)
    
    def scheduling_a_run(self, sha, num_nodes, title, requester):
        sql = "INSERT INTO requests ( sha, num_nodes, title, requester, status) values (%s, %s, %s, %s, 'PENDING')"
        result = self.execute_sql(sql, ( sha, num_nodes, title, requester))
        request_id = result.lastrowid
        return request_id

    def get_instances(self, num_nodes, request_id):
        sql = "SELECT ip FROM instances WHERE status='AVAILABLE' LIMIT %s"
        result =  self.execute_sql(sql,(num_nodes,)).fetchall()
        if len(result) < num_nodes:
            return []
        instances = []
        for i in range(0, len(result)):
            sql = "UPDATE instances SET status='TAKEN', request_id=%s WHERE ip=%s"
            self.execute_sql(sql,(request_id, result[i]['ip']))
            instances.append(result[i]['ip'])
        return instances
    
    def get_instances_status(self, ips):
        num = ','.join(['%s'] * len(ips))
        sql = "SELECT ip, status FROM instances WHERE ip IN (%s)" % num
        result =  self.execute_sql(sql, tuple(ips)).fetchall()
        ret = {}
        for r in result:
            ret[r['ip']] = r['status']
        return ret

    def cancel_the_run(self, request_id):
        sql = "UPDATE requests SET status = 'CANCELED' WHERE id = %s"
        self.execute_sql(sql, (request_id,))
        sql = "SELECT ip from instances WHERE request_id=%s"
        result = self.execute_sql(sql, (request_id,))
        return [r['ip'] for r in result ]

    def free_instances(self, request_id):       
        sql = "UPDATE instances SET status = 'AVAILABLE', request_id=null WHERE request_id = %s"
        self.execute_sql(sql, (request_id,))
        
