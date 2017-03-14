from ctypes import *
lib = cdll.LoadLibrary('./MainNode/libMainNode.so')

class MainNode(object):
    def __init__(self, imagefunc):
        self.obj = lib.MainNode_new()
        self.imagefunc = imagefunc

        # set img callback
        self.FUNC1 = CFUNCTYPE(None, c_int, POINTER(c_ubyte))
        self.func1 = self.FUNC1(self.imagefunc)
        lib.MainNode_setImageCallback(self.obj, self.func1)

    def steer(self, angle):
    	lib.steer(angle)

    def connectPolySync(self):
        lib.MainNode_connectPolySync(self.obj)