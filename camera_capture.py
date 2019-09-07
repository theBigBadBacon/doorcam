import app_config
import logging
import RPi.GPIO as GPIO
from flask import Flask, render_template, Response, request
from flask_socketio import SocketIO, emit
from flask_basicauth import BasicAuth
from camera_pi import Camera

app = Flask(__name__)

app.config['SECRET_KEY'] = app_config.env['secret']
app.config['BASIC_AUTH_USERNAME'] = app_config.env['auth_user']
app.config['BASIC_AUTH_PASSWORD'] = app_config.env['auth_pass']

basic_auth = BasicAuth(app)
socketio = SocketIO(app)
override = app_config.env['override']

def ring_doorbell(channel):
    app.logger.warning('Doorbell is ringing')
    socketio.emit('doorbell', 'ringing')
    return True

GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(10,GPIO.RISING,callback=ring_doorbell,bouncetime=500)

@app.route('/')
@basic_auth.required
def index():
    return render_template('doorcam.html')

@app.route('/' + override)
def frame():
    ring_doorbell(None)
    return render_template('doorcam.html')

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    else:
        GPIO.cleanup()

@app.route('/video_feed')
def video_feed():
    return Response(gen(Camera()),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on_error()        # Handles the default namespace
def error_handler(e):
    GPIO.cleanup()
    app.logger.warning('Error',e)
    pass

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port =8000)
