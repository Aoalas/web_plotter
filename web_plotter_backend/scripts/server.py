#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import rostopic
import threading
import os
import sys
import datetime
import time
import copy

from flask import Flask, render_template, request, send_from_directory, jsonify, make_response
from flask_socketio import SocketIO, emit
from rospy_message_converter import message_converter

script_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(script_dir, 'templates')

static_dir = os.path.join(script_dir, 'static')


app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = 'robomaster_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

lock = threading.Lock()

subscribers = {}
latest_payloads = {}

def get_time_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

def background_thread():
    global latest_payloads
    rate = 20.0
    period = 1.0 / rate
    print(f"[{get_time_str()}] [SYSTEM] Background publisher started at {rate}Hz")

    while True:
        start_time = time.time()

        with lock:
            current_data = copy.deepcopy(latest_payloads)

        if current_data:
            batch_payload = []
            for topic, payload in current_data.items():
                batch_payload.append(payload)

            if batch_payload:
                try:
                    socketio.emit('ros_data_batch', batch_payload)
                except:
                    pass

        elapsed = time.time() - start_time
        if period - elapsed > 0:
            time.sleep(period - elapsed)

def ros_callback(msg, topic_name):
    global latest_payloads
    try:
        data_dict = message_converter.convert_ros_message_to_dictionary(msg)
        with lock:
            latest_payloads[topic_name] = {
                'topic': topic_name,
                'timestamp': rospy.get_time(),
                'msg': data_dict
            }
    except Exception as e:
        pass

@socketio.on('connect')
def on_connect():
    print(f"[{get_time_str()}] [CONNECT] Client: {request.remote_addr}")
    emit('server_log', {'level': 'success', 'msg': f"Connected."})
    with lock:
        for topic in subscribers.keys():
            emit('subscribe_ack', {'topic': topic})

@socketio.on('disconnect')
def on_disconnect():
    print(f"[{get_time_str()}] [DISCONNECT] Client disconnected")

@app.route('/')
def index():
    return send_from_directory(template_dir, 'index.html')

@app.route('/topics')
def get_topics():
    try:
        topics = rospy.get_published_topics()
        topic_list = [{'name': t[0], 'type': t[1]} for t in topics]
        response = make_response(jsonify({'topics': topic_list}))
    except Exception as e:
        response = make_response(jsonify({'topics': [], 'error': str(e)}))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@socketio.on('subscribe')
def handle_subscribe(data):
    global subscribers
    topic_name = data.get('topic')
    if not topic_name: return

    with lock:
        if topic_name not in subscribers:
            msg_class, _, _ = rostopic.get_topic_class(topic_name)
            if msg_class is None:
                emit('server_log', {'level': 'error', 'msg': f"Type not found: {topic_name}"})
                return

            print(f"[{get_time_str()}] [SUB] {topic_name}")
            subscribers[topic_name] = rospy.Subscriber(
                topic_name,
                msg_class,
                callback=lambda msg: ros_callback(msg, topic_name)
            )
        emit('subscribe_ack', {'topic': topic_name})

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    global subscribers, latest_payloads
    topic_name = data.get('topic')
    if not topic_name: return

    with lock:
        if topic_name in subscribers:
            subscribers[topic_name].unregister()
            del subscribers[topic_name]

        if topic_name in latest_payloads:
            del latest_payloads[topic_name]

        print(f"[{get_time_str()}] [UNSUB] {topic_name}")
        emit('server_log', {'level': 'info', 'msg': f"Unsubscribed {topic_name}"})

if __name__ == '__main__':
    rospy.init_node('web_plotter_backend', anonymous=True)
    bg_thread = threading.Thread(target=background_thread)
    bg_thread.daemon = True
    bg_thread.start()

    print(f"[{get_time_str()}] Backend Running on port 5000")
    socketio.run(app, host='0.0.0.0', port=5000)