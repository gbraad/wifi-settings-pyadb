import Tkinter as Tk
import sys
import os
import glob
import socket
import json
import re
workpath = os.path.dirname(sys.argv[0])


fields = "wifi-name", "wifi-type", "wifi-bssid", "wifi-password", "timezone"
if sys.platform.startswith("win"):
    # the latest version works under windows
    sys.path.insert(0, os.path.join(workpath, "modules", "pyadb-master"))
    from pyadb import ADB
    adb = ADB(os.path.join(workpath, "adb-win", "adb"))
elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
    # this old version works under linux
    sys.path.insert(0, os.path.join(workpath, "modules", "pyadb-81712c4"))
    from pyadb import ADB
    adb = None

    for i in os.environ['PATH'].split(':'):
        if len(glob.glob(os.path.join(i, "adb"))) > 0:
            adb = ADB(glob.glob(os.path.join(i, "adb"))[0])
            break
    if adb == None:
        if sys.platform.startswith("linux"):
            adb = ADB(os.path.join(workpath, "adb-linux", "adb"))
        elif sys.platform.startswith("darwin"):
            adb = ADB(os.path.join(workpath, "adb-darwin", "adb"))


def save_config(variables):
    from tkFileDialog import asksaveasfilename
    import pickle
    file = asksaveasfilename()
    if len(file) > 0:
        db = {}
        for i in range(0, len(fields)):
            db[fields[i]] = variables[i].get()
        print "save to " + file
        fd = open(file, 'w')
        pickle.dump(db, fd)
        fd.close()
    elif len(file) == 0:
        print "save cancelled"


def load_config(variables):
    from tkFileDialog import askopenfilename
    import pickle
    file = askopenfilename()
    if len(file) > 0:
        print "load from " + file
        fd = open(file)
        db = pickle.load(fd)
        fd.close()
        for i in range(0, len(fields)):
            variables[i].set(db[fields[i]])
    elif len(file) == 0:
        print "load cancelled"


def configure(variables):
    adb.wait_for_device()
    adb.forward_socket("tcp:8881", "tcp:8881")

    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.connect(("127.0.0.1", 8881))

    # register to configd
    register = {}
    register["protocol_version"] = "1.0"
    register["meta"] = {"reply": False}
    register["message_type"] = "register"
    register["data"] = {"name": "wifi-setting"}
    data = json.dumps(register, separators=(',', ':'))
    so.send("%d:%s" % (len(data), data))

    # query the key_code
    command = {}
    command["protocol_version"] = "1.0"
    command["meta"] = {"reply": True}
    command["message_type"] = "command"
    query = {}
    query["command"] = "query"
    query["type"] = "key_code"
    query["ap_mac"] = adb.shell_command("cat /sys/class/net/wlan0/address").strip()
    query["imei"] = "359209020201699"
    command["data"] = query
    data = json.dumps(command, separators=(',', ':'))
    so.send("%d:%s" % (len(data), data))
    # receive key_code
    data = so.recv(4096)
    key_code = json.loads(re.match('[0-9]*:(.*)', data).group(1))['data']['key_code']

    # send the wifi config
    command["meta"] = {"reply": False}
    setting = {}
    setting["command"] = "setting"
    setting["wifi-hidden"] = False
    setting["name"] = "MatchStick" + key_code
    setting["type"] = "wifi"
    setting["key"] = key_code
    for i in range(0, len(variables)):
        setting[fields[i]] = variables[i].get()
    command["data"] = setting
    data = json.dumps(command, separators=(',', ':'))
    data = data.replace('/', '\/')
    so.send("%d:%s" % (len(data), data))
    so.close()


def makeform(root, fields):
    form = Tk.Frame(root)
    form.pack(fill=Tk.X)

    # get the width
    width = 0
    for field in fields:
        if len(field) > width:
            width = len(field)

    variables = []
    for field in fields:
        row = Tk.Frame(form)
        row.pack(side=Tk.TOP, fill=Tk.X)
        left = Tk.Frame(row)
        rite = Tk.Frame(row)

        left.pack(side=Tk.LEFT)
        rite.pack(side=Tk.RIGHT, expand=Tk.YES, fill=Tk.X)

        lab = Tk.Label(left, width=width, text=field, anchor=Tk.W)
        ent = Tk.Entry(rite)
        lab.pack(side=Tk.LEFT)
        ent.pack(side=Tk.TOP, fill=Tk.X)
        var = Tk.StringVar()
        ent.config(textvariable=var)
        variables.append(var)
    return variables

if __name__ == '__main__':
    root = Tk.Tk()
    vars = makeform(root, fields)
    frame_l = Tk.Frame(root)
    frame_r = Tk.Frame(root)
    frame_l.pack(side=Tk.LEFT)
    frame_r.pack(side=Tk.RIGHT, fill=Tk.X)

    # button: Configure, Quit
    btnc = Tk.Button(frame_r, text='Configure', command=(lambda: configure(vars)))
    btnq = Tk.Button(frame_r, text='Quit!', command=root.quit)
    btnq.pack(side=Tk.RIGHT)
    btnc.pack(side=Tk.RIGHT)
    # button: Save, Load
    btns = Tk.Button(frame_l, text='Save', command=(lambda: save_config(vars)))
    btnl = Tk.Button(frame_l, text='Load', command=(lambda: load_config(vars)))
    btns.pack(side=Tk.LEFT)
    btnl.pack(side=Tk.LEFT)

    root.mainloop()
