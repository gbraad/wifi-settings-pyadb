import Tkinter as Tk
import sys
import os
import glob
import re
import thread
import time
workpath = os.path.dirname(sys.argv[0])


fields = "netperf-server", "single-duration", "test-times"
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


def start_test(variables):
    adb.wait_for_device()
    db = {}
    for i in range(0, len(variables)):
        db[fields[i]] = variables[i].get()
    for i in range(0, int(db["test-times"])):
        print ("%02d: " % (i+1)) + adb.shell_command("netperf -t TCP_STREAM -l %s -P 0 -H %s" % (db["single-duration"], db["netperf-server"]))


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


def status_check(c, s, v, o):
    last_list = None
    while True:
        r = adb.get_devices()
        if r[0] == 0 and len(r[1]) > 0:
            # green and normal
            c.itemconfig(s, fill='green')
            btnc['state'] = 'normal'
            if last_list != r[1]:
                menu = o['menu']
                menu.delete(0, Tk.END)
                for i in range(0, len(r[1])):
                    menu.add_command(label=r[1][i], command=(lambda sn=r[1][i]: v.set(sn)))
                if len(v.get()) > 0 and v.get() in r[1]:
                    print 'already set'
                else:
                    v.set(r[1][0])
                last_list = r[1]
        else:
            # red and disable
            c.itemconfig(s, fill='red')
            btnc['state'] = 'disabled'
            if last_list != r[1]:
                menu = o['menu']
                menu.delete(0, Tk.END)
                v.set('')
            last_list = []
        time.sleep(1)


def sn_set(*args):
    print "sn_set: [%s]" % (v.get())
    if len(v.get()) > 0:
        adb.set_target_device(v.get())

if __name__ == '__main__':
    root = Tk.Tk()
    # top
    frame_t = Tk.Frame(root)
    frame_t.pack(side=Tk.TOP, anchor=Tk.W, fill=Tk.X)
    c = Tk.Canvas(frame_t, width=50, height=50)
    c.pack(side=Tk.LEFT)
    s = c.create_oval(10, 10, 40, 40)

    v=Tk.StringVar()
    v.trace('w', sn_set)
    o=Tk.OptionMenu(frame_t, v, '')
    o.pack(side=Tk.RIGHT)

    # middle
    vars = makeform(root, fields)
    # bottom
    frame_l = Tk.Frame(root)
    frame_r = Tk.Frame(root)
    frame_l.pack(side=Tk.LEFT)
    frame_r.pack(side=Tk.RIGHT, fill=Tk.X)

    # button: Start, Quit
    btnc = Tk.Button(frame_r, text='Start', command=(lambda: start_test(vars)))
    btnq = Tk.Button(frame_r, text='Quit!', command=root.quit)
    btnq.pack(side=Tk.RIGHT)
    btnc.pack(side=Tk.RIGHT)
    # button: Save, Load
    btns = Tk.Button(frame_l, text='Save', command=(lambda: save_config(vars)))
    btnl = Tk.Button(frame_l, text='Load', command=(lambda: load_config(vars)))
    btns.pack(side=Tk.LEFT)
    btnl.pack(side=Tk.LEFT)

    # thread and loop
    thread.start_new(status_check, (c, s, v, o))
    root.mainloop()
