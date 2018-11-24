#!/usr/bin/env python3

import sys
import struct
import numpy
import threading
import binascii
import time
import os
import readline
import traceback
import dbus
import dbus.service
import dbus.exceptions
import itertools

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
from dbus.mainloop.glib import DBusGMainLoop

MESH_SERVICE_NAME = 'org.bluez.mesh1'
MESH_SERVICE_PATH = "/org/bluez/mesh1"
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'

MESH_NETWORK_IFACE = 'org.bluez.mesh1.Network'
MESH_NODE_IFACE = 'org.bluez.mesh1.Node'
MESH_ELEMENT_IFACE = 'org.bluez.mesh1.Element'

VENDOR_ID_NONE = 0xffff

PUBLISH_REPEAT_N = 5

app = None
bus = None
mainloop = None
node = None
composition = []
token = numpy.uint64(0x76bd4f2372477600)


# ANSI escape codes for Select Graphic Rendition (SGR) parameters
sgr_reset = "\x1B[0m"
sgr_fg_blue = "\x1B[94m"
sgr_fg_green = "\x1B[32m"
sgr_fg_red = "\x1B[31m"


class SigUnit:
  celsius_temperature = 0x272F


def get_my_name():
  """Returns name of the script without extension"""
  script_name = os.path.basename(sys.argv[0]) # in case it is full path
  script_name_no_ext = os.path.splitext(script_name)[0]

  return script_name_no_ext


def unwrap(item):
    if isinstance(item, dbus.Boolean):
        return bool(item)
    if isinstance(item, (dbus.UInt16, dbus.Int16,
                         dbus.UInt32, dbus.Int32,
                         dbus.UInt64, dbus.Int64)):
        return int(item)
    if isinstance(item, dbus.Byte):
        return bytes([int(item)])
    if isinstance(item, dbus.String):
            return item
    if isinstance(item, (dbus.Array, list, tuple)):
        return [unwrap(x) for x in item]
    if isinstance(item, (dbus.Dictionary, dict)):
        return dict([(unwrap(x), unwrap(y)) for x, y in item.items()])

    print('Dictionary item not handled')
    print(type(item))
    return item


def attach_app_cb(node_path, dict_array):
    print('Mesh application registered ', node_path)
    print(type(node_path))
    print(type(dict_array))
    print(dict_array)

    els = unwrap(dict_array)
    print("Get Elements")
    for el in els:
        print(el)
        idx = struct.unpack('b', el[0])[0]
        print('Configuration for Element ')
        print(idx)
        models = el[1]

        element = app.get_element(idx)
        element.set_model_config(models)

    obj = bus.get_object(MESH_SERVICE_NAME, node_path)
    global node
    node = dbus.Interface(obj, MESH_NODE_IFACE)


def error_cb(error):
    print('D-Bus call failed: ' + str(error))


def generic_reply_cb():
    print('D-Bus call done')


def interfaces_removed_cb(object_path, interfaces):
    if not mesh_net:
        return

    if object_path == mesh_net[2]:
        print('Service was removed')
        mainloop.quit()


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/example'
        self.elements = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_element(self, element):
        self.elements.append(element)

    def get_element(self, idx):
        for ele in self.elements:
            if ele.get_index() == idx:
                return ele

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')
        for element in self.elements:
            response[element.get_path()] = element.get_properties()
        return response


class Element(dbus.service.Object):
    PATH_BASE = '/example/ele'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + format(index, '02x')
        print(self.path)
        self.models = []
        self.bus = bus
        self.index = index
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                MESH_ELEMENT_IFACE: {
                }
        }

    def add_model(self, model):
        model.set_path(self.path)
        self.models.append(model)

    def get_index(self):
        return self.index

    def set_model_config(self, config):
        print('Set element models config')

    @dbus.service.method(MESH_ELEMENT_IFACE,
                                        in_signature="qqqay", out_signature="")
    def MessageReceived(self, dest, source, key, data):
        print('Received message: dest = {:#x}, source = {:#x}, key = {}, ' \
            'data = {}'.format(dest, source, key, data))
        for model in self.models:
            model.process_message(source, key, data)

    @dbus.service.method(MESH_ELEMENT_IFACE, in_signature="", out_signature="")
    def get_path(self):
        return dbus.ObjectPath(self.path)


class Model():
    def __init__(self, model_id=None, vnd_id=None):
        self.cmd_ops = None
        self.model_id = model_id
        self.vendor_id = vnd_id
        self.path = None

    def set_path(self, path):
        self.path = path

    def process_message(self, source, key, data):
        print('Model process message')

    def set_publication(self, period):
        self.period = period

    def set_bindings(self, bindings):
        self.bindings = bindings

    def set_subscriptions(self, subs):
        self.subs = subs


class VndTextClient(Model):
    def __init__(self, mid):
        Model.__init__(self, vnd_id=mid)
        self.HELLO_OP = 0xfbf105
        self.PATIENT_OP = 0xfd05f1
        self.cmd_ops = {
                        self.HELLO_OP: self.hello_text,
                        self.PATIENT_OP: self.patient_text,
                      }

    def _reply_cb(state):
      print('State ', state);
      mainloop.quit()

    def _send_message(self, dest, key, data, reply_cb):
        node.Send(self.path, dest, key, data, reply_handler=reply_cb,
                  error_handler=error_cb)

    def hello_text(self, dst_str=None, key_idx_str=None, text_str=None):
        print("{}: {} {} {}".format(self.hello_text.__name__, dst_str, key_idx_str, text_str))

        if dst_str == None or key_idx_str == None or text_str == None:
            print("Wrong {} parameters".format(self.hello_text.__name__))
            print("\tdst_addr key_index text")
            print("\n\texample: 29537 0 Participant")

            return

        text_str = ''.join((text_str, '\x00'))

        opcode = self.HELLO_OP
        dst = int(dst_str, 0)
        key_idx = int(key_idx_str)
        b_text = text_str.encode('ASCII')

        data = struct.pack('%ds' % len(b_text), b_text)
        data = opcode.to_bytes(3, byteorder='big') + data

        self._send_message(dst, key_idx, data, self._reply_cb)


    def patient_text(self, dst_str=None, key_idx_str=None, text_str=None):
        print("{}: {} {} {}".format(self.patient_text.__name__, dst_str, key_idx_str, text_str))

        if dst_str == None or key_idx_str == None or text_str == None:
            print("Wrong {} parameters".format(self.patient_text.__name__))
            print("\tdst_addr key_index text")
            print("\n\texample: 29537 0 Participant")

            return

        text_str = ''.join((text_str, '\x00'))

        opcode = self.PATIENT_OP
        dst = int(dst_str, 0)
        key_idx = int(key_idx_str)
        b_text = text_str.encode('ASCII')

        data = struct.pack('%ds' % len(b_text), b_text)
        data = opcode.to_bytes(3, byteorder='big') + data

        self._send_message(dst, key_idx, data, self._reply_cb)


    def process_message(self, source, key, data):
        print("{}, {}: {} {} {}".format(self.__class__.__name__,
            self.process_message.__name__, source, key, data))

        b_data = bytearray(data)

        datalen = len(b_data)

        opcode = int.from_bytes(b_data[:3], 'big')

def attach_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


def cmd_handler(cmd_line):
    model = None
    op = None
    args = cmd_line.split()

    if len(args) < 4:
        print ("Not enough arguments!")
        return

    element_idx = int(args[0])
    model_id = int(args[1], 0)
    op = int(args[2], 0)

    if len(args) >= 4:
        data = args[3:]

    available_element_idxs = [element.index for element in app.elements]
    if element_idx not in available_element_idxs:
        print("No element index =", element_idx)
        print("Available element indexes =", available_element_idxs)

        return

    models = app.elements[available_element_idxs.index(element_idx)].models
    available_models_id = [model.model_id for model in models]
    available_vnd_models_id = [model.vendor_id for model in models]
    if model_id in available_models_id:
        model = models[available_models_id.index(model_id)]
    elif model_id in available_vnd_models_id:
        model = models[available_vnd_models_id.index(model_id)]
    else:
        print("No model with id =", model_id)
        print("Available models id =", [hex(x) for x in available_models_id if x is not None])
        print("Available vnd models id =", [hex(x) for x in available_vnd_models_id if x is not None])

        return

    ops = model.cmd_ops
    if op not in ops:
        print("No op =", hex(op))
        print("Available ops =", ["0x" + format(op_hex, 'x') for op_hex in ops])

        return

    ops[op](*data)


# print("\te.g. model element_index model_index opcode dst_addr key_index [data]")

def cmd_generic_handler(cmd_line):
  # Give time for application setup
  time.sleep(1)

  if cmd_line.split()[0] == "model":
    for _ in itertools.repeat(None, PUBLISH_REPEAT_N):
      cmd_handler(cmd_line[5:])
  else:
    print("non option")

  return False


def main():
  DBusGMainLoop(set_as_default=True)

  global bus
  bus = dbus.SystemBus()
  global mainloop
  global app

  mesh_net = dbus.Interface(
      bus.get_object(MESH_SERVICE_NAME, MESH_SERVICE_PATH), MESH_NETWORK_IFACE
  )
  mesh_net.connect_to_signal('InterfacesRemoved', interfaces_removed_cb)

  app = Application(bus)
  first_ele = Element(bus, 0x00)
  first_ele.add_model(VndTextClient(0x0000))
  app.add_element(first_ele)

  mainloop = GObject.MainLoop()

  print('Attach to meshnet')
  mesh_net.Attach(app.get_path(), token,
                  reply_handler=attach_app_cb,
                  error_handler=attach_app_error_cb)

  exec_param_str = ' '.join(sys.argv[1:])
  t_exec = threading.Thread(target=cmd_generic_handler, args=[exec_param_str])
  t_exec.start()

  try:
    mainloop.run()
  except:
    import traceback
    traceback.print_exc()
    sys.exit(16)





if __name__ == '__main__':
    main()
