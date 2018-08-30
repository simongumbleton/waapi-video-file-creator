import os
import sys

import asyncio

import tkinter
from tkinter import *
from tkinter import filedialog

import fnmatch

from autobahn.asyncio.wamp import ApplicationRunner
from ak_autobahn import AkComponent

from waapi import WAAPI_URI



class MyComponent(AkComponent):


    def onJoin(self, details):
        ###### Function definitions #########

        def exit():
            self.leave()

        def beginUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_begingroup)

        def cancelUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_cancelgroup)

        def endUndoGroup():
            undoArgs = {"displayName": "Create objetcs from video files"}
            self.call(WAAPI_URI.ak_wwise_core_undo_endgroup, {}, **undoArgs)

        def saveWwiseProject():
            self.call(WAAPI_URI.ak_wwise_core_project_save)

        def askUserForImportDirectory():
            root = tkinter.Tk()
            root.withdraw()
            root.update()
            dir = filedialog.askdirectory(title="Choose source directory")
            root.update()
            root.destroy()
            return dir

        def setupSourceFileList(path):
            # print("Setting up list of audio files")
            filelist = []
            pattern = '*.wav'

            for root, dirs, files in os.walk(path):
                # for file in os.listdir(path):
                for filename in fnmatch.filter(files, pattern):
                    absFilePath = os.path.abspath(os.path.join(root, filename))
                    filelist.append(absFilePath)
            return filelist

        def setupCreateArgs(parentID ,otype = "BlendContainer",  oname = "" , conflict = "merge"):
            createObjArgs = {

                "parent": parentID,
                "type": otype,
                "name": oname,
                "onNameConflict": conflict
            }
            return createObjArgs

        def EventCreateArgs(parentID ,fname, targets, action = 1):

            createObjArgs = {

                "parent": parentID,
                "type": "Event",
                "name": "PlayClip_"+fname,
                "onNameConflict": "merge",
                "children": [
                {   "name": "0",
                    "type": "Action",
                    "@ActionType": action, #22 = set state
                    "@Target": targets[0] },
                {   "name": "1",
                    "type": "Action",
                    "@ActionType": action,  # 22 = set state
                    "@Target": targets[1]},
                {   "name": "2",
                    "type": "Action",
                    "@ActionType": action,  # 22 = set state
                    "@Target": targets[2]},
                {   "name": "3",
                    "type": "Action",
                    "@ActionType": 22,  # 22 = set state
                    "@Target": targets[3]}
                ]
            }
            return createObjArgs

        def createWwiseObject(args):
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_create, {}, **args)
            except Exception as ex:
                print("call error: {}".format(ex))



        ###### Main logic flow #########
        try:
            res = yield from self.call(WAAPI_URI.ak_wwise_core_getinfo)  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))


        #####  Do Some Cool stuff here #######

        sourceDir = os.path.expanduser(askUserForImportDirectory())
        print(sourceDir)

        sourceFiles = setupSourceFileList(sourceDir)

        beginUndoGroup()

        for file in sourceFiles:
            fpath = os.path.abspath(file)
            fbase = os.path.dirname(file)
            fbase = os.path.basename(fbase)
            f = file.rsplit('.')
            fname = os.path.basename(f[0])
            #print(fname)

            VoParent = "\\Actor-Mixer Hierarchy\\VO\\"
            sfxParent = "\\Actor-Mixer Hierarchy\\SFX\\"
            foleyParent = "\\Actor-Mixer Hierarchy\\Foley\\"
            stateParent = "\\States\\Default Work Unit\\"
            eventParent = "\\Events\\Default Work Unit\\"

            args = setupCreateArgs(VoParent,"ActorMixer",fbase)
            yield from createWwiseObject(args)
            args = setupCreateArgs(sfxParent,"ActorMixer",fbase)
            yield from createWwiseObject(args)
            args = setupCreateArgs(foleyParent,"ActorMixer",fbase)
            yield from createWwiseObject(args)
            args = setupCreateArgs(stateParent,"StateGroup",fbase)
            yield from createWwiseObject(args)
            args = setupCreateArgs(eventParent,"Folder",fbase)
            yield from createWwiseObject(args)

            args = setupCreateArgs(VoParent+fbase+"\\","BlendContainer",fname)
            yield from createWwiseObject(args)
            args = setupCreateArgs(sfxParent+fbase+ "\\", "BlendContainer", fname)
            yield from createWwiseObject(args)
            args = setupCreateArgs(foleyParent+fbase+ "\\", "BlendContainer", fname)
            yield from createWwiseObject(args)
            args = setupCreateArgs(stateParent+fbase+ "\\", "State", fname)
            yield from createWwiseObject(args)


            eventTargets = [
                VoParent + fbase + "\\" + fname,
                sfxParent + fbase + "\\" + fname,
                foleyParent + fbase + "\\" + fname,
                stateParent + fbase + "\\" + fname
            ]

            args = EventCreateArgs(eventParent+fbase+"\\",fname,eventTargets)
            yield from createWwiseObject(args)



        print("done!")

        endUndoGroup()

        saveWwiseProject()

        exit()


    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")
    try:
        runner.run(MyComponent)
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
