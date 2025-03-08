import json
import re
import os
import tkinter
from tkinter import Tk, Frame, Entry, Button, Label, Scrollbar, Canvas, BooleanVar, IntVar, StringVar, ttk, END, Toplevel
import time
import math
import re
import os
import sys
from tkinter.colorchooser import askcolor

from typing import Callable, List, Tuple, Any, Dict

try:  
    import serial.tools.list_ports
except:
    pass

myDict = {}
modParamterDict = {}

global intCount
global floatCount
intCount = 0
floatCount = 0

floatReg = r'-?\d*\.?\d+'


gridKwargs = dict(padx=1, pady=1, sticky='wens')
packKwargs = dict(padx=1, pady=1)

def SecondsToDurationStampe(timeInSeconds, roundPlace=3, returnSecondsOnly=False):
    if timeInSeconds >= 86400:
        timeInSeconds, days    = SecondsToDays(timeInSeconds)
        timeInSeconds, hours   = SecondsToHours(timeInSeconds)
        timeInSeconds, minutes = SecondsToMinutes(timeInSeconds)
        seconds = round(timeInSeconds, roundPlace)
        returnString = "{}d {}h {}m {}s".format(days, hours, minutes, seconds)
    elif timeInSeconds >= 3600:
        timeInSeconds, hours   = SecondsToHours(timeInSeconds)
        timeInSeconds, minutes = SecondsToMinutes(timeInSeconds)
        seconds = round(timeInSeconds, roundPlace)
        returnString = "{}h {}m {}s".format(hours, minutes, seconds)
    elif timeInSeconds >= 60:
        timeInSeconds, minutes = SecondsToMinutes(timeInSeconds)
        seconds = round(timeInSeconds, roundPlace)
        returnString = "{}m {}s".format(minutes, seconds)
    else: #if less than a minutes
        if returnSecondsOnly:
            returnString = round(timeInSeconds, roundPlace)
        else:
            returnString = ''
    return returnString

def SecondsToDays(timeInSeconds):
    days = math.floor(timeInSeconds / 86400)
    remainder = timeInSeconds - (days * 86400)

    return remainder, days

def SecondsToHours(timeInSeconds):
    hours = math.floor(timeInSeconds / 3600)
    remainder = timeInSeconds - (hours * 3600)

    return remainder, hours

def SecondsToMinutes(timeInSeconds):
    minutes = math.floor(timeInSeconds / 60)
    remainder = timeInSeconds - (minutes * 60)

    return remainder, minutes

def RGB(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

def FloatRGB(r, g, b):
    r = int(r*255)
    g = int(g*255)
    b = int(b*255)
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

def UpdatePortList():
    '''pull from "Ports" under device manager. Parse the results'''
    '''portDict [ComX]: Description'''
    '''portList [ComX, ComY...]'''
    deviceList = list(serial.tools.list_ports.comports()) # BUG this line is taking 11 seconds? Fixed by restarting computer.
    if deviceList == 0:
        deviceList = ['None - No Devices Found']
    portDict = {}
    portList = []
    for item in deviceList:
        portParse = re.match(r'(\w*) - (.*) \(*',str(item))
        if portParse == None:
            portDict[item[0]] = item[1]
            portList.append(item[0])
        else:
            portDict[portParse.group(1)] = portParse.group(2)
            portList.append(portParse.group(1))
    portList.sort()
    return portList, portDict

def Button_WorkStart(button:Button, workingColor="yellow"):
    button.config(bg=workingColor, state="disabled")

def Button_ParseBool(button:Button, success:bool, successColor="lightgreen", failColor="lightsalmon") -> bool:
    """Will enable button and change color based on success

    Args:
        button (Button): self
        success (bool): Was the action successful
        successColor (str, optional): Color for success. Defaults to "lightgreen".
        failColor (str, optional): Color for failure. Defaults to "lightsalmon".

    Returns:
        bool: Return success as it was passed it. Allows it to be used in an if statement to condense code
    """    
    myColor = successColor if success else failColor
    button.config(bg=myColor, state="normal")
    return success

Button.WorkStart = Button_WorkStart
Button.ParseBool = Button_ParseBool

class ColorButton(Button):
    def __init__(self, frame, initialColor='#FF0000', *args, **kwargs):
        Button.__init__(self, frame, *args, **kwargs)
        self.color = initialColor

        self.config(command=self.SelectColor, bg=self.color)
        self.bind('<Button-3>', self.PrintColor)

    def PrintColor(self, event=None):
        print(self.rgb)
        

    def SelectColor(self):
        color = askcolor()

        if color != (None, None):
            self.color = color[1]
            self.config(bg=self.color)

    def SetColor(self, color):
        self.color = color
        self.config(bg=self.color)

    @property
    def rgb(self):
        r = int(self.color[1:3], 16)
        g = int(self.color[3:5], 16)
        b = int(self.color[5:7], 16)

        return [r, g, b]

class PortMenu(ttk.Combobox):
    def __init__(self, frame, TextDisplay=None, autoSelect='', *args, **kwargs):
        ttk.Combobox.__init__(self, frame, *args, **kwargs)
        self.frame = frame
        self.TextDisplay = TextDisplay
        self.autoSelect = autoSelect

        self.autoPortFound = False

        if 'width' not in kwargs.keys():
            self.config(width=7)

        
        self.portList, self.portDict = UpdatePortList()
        
        if self.portList == []: self.portList = ["None"]

        #self.portMenu = ttk.Combobox(self.frame, values = self.portList, width=6)
        self.bind('<Button-1>', self.RefreshPorts)

        
        self.RefreshPorts(doForceUpdate=True)
        
    def SelectIfAvailable(self, desiredComPort:str):
        if desiredComPort.upper() in self.portList:
            self.set(desiredComPort)

    def RefreshPorts(self, event=None, doForceUpdate:bool = False):
        if self.cget("state") != "normal" and not doForceUpdate:
            return

        currentPort = self.get()
        self.portList, self.portDict = UpdatePortList()
        self.portList.sort()
        autoSelectPort = None

        self.autoPortFound = False
        
        if self.TextDisplay is not None:
            self.TextDisplay('Port Descriptions:', True)
            for item in self.portList:
                self.TextDisplay('{:<5} - {}'.format(item, self.portDict[item]))
                if self.portDict[item] == self.autoSelect:
                    autoSelectPort = item
                    self.autoPortFound = True
        
        self.config(values = self.portList)

        if autoSelectPort is not None:
            self.set(autoSelectPort)
        else:
            if currentPort in self.portList:
                self.set(currentPort)
            else:
                self.set(self.portList[0])

class TimeEntry(Entry):
    def __init__(self, myFrame, width=19, maxLength=None, *args, **kwargs):
        Entry.__init__(self, myFrame, *args, **kwargs)
                
        self.myFrame = myFrame
        self.width = width
        self.maxLength = maxLength
        
        #validFloat = (self.modOptionFrame.register(ValidateFloatInput), '%P', '%S', '%d', '%s')
        
        self.timeEntry = Entry(self)
        validTime = (self.timeEntry.register(self.ValidTimeInput), '%P', '%S', '%d', '%s')
        self.config(validate='key')
        self.config(validatecommand=validTime)
        self.timeEntry.bind('<KeyRelease>', self.FormatTime)
        
    def FormatTime(self, event=None):
        if event.keysym in ['BackSpace', 'Delete']: 
            return
        textLenth = len(self.timeEntry.get())
        if textLenth in [4, 7]:
            self.timeEntry.insert(textLenth, '-')
        elif textLenth == 10:
            self.timeEntry.insert(textLenth, ' ')
        elif textLenth in [13,16]:
            self.timeEntry.insert(textLenth, ':')
        
    def ValidTimeInput(self, post_text, text, action, prev_text):
        if len(text) == 19: return True
        if action == '1':
            if len(prev_text) < 4:
                if text.isdigit():
                    return True
                else:
                    return False
            elif len(prev_text) in [4, 7]:
                if text in ['-', '/', '\\']:
                    return True
                else:
                    return False
            elif len(prev_text) < 7:
                if text.isdigit():
                    return True
                else:
                    return False
            elif len(prev_text) == 10:
                if text == ' ':
                    return True
                else:
                    return False
            elif len(prev_text) in [13, 16]:
                if text == ':':
                    return True
                else:
                    return False
            elif len(prev_text) < 13:
                if text.isdigit():
                    return True
                else:
                    return False
            elif len(prev_text) < 16:
                if text.isdigit():
                    return True
                else:
                    return False
            elif len(prev_text) < 19:
                if text.isdigit():
                    return True
                else:
                    return False
            else: return False
            
                
        elif action == "0":
            return True

class FloatEntry(Entry):
    def __init__(self, myFrame, *args, **feParams):
        Entry.__init__(self, myFrame, *args, **feParams)
                
        self.myFrame = myFrame
        self.width = feParams.get('width', 16)

        self.validFloat = (self.register(self.ValidateFloatInput), '%P', '%S', '%d', '%s')
        self.config(validate='key')
        self.config(validatecommand=self.validFloat)

    def ChangeState(self, state):
        self['state'] = state
        
    def ValidateFloatInput(self, value_if_allowed, text, action, prev_text):
        if len(text) > 1: return True
        if action == '1':
            if len(text) > 1:
                try:
                    float(text)
                    return True
                except:
                    return False
            if len(prev_text) >= self.width:
                return False
            if text.isdigit():
                try:
                    float(value_if_allowed)
                    return True
                except:
                    return False
            elif text == '.' or text == '-':
                if re.search(r'\.', prev_text):    
                    return False
                else:
                    return True
            else:
                return False
        elif action == "0":
            return True

class HexEntry(Entry):
    def __init__(self, myFrame, maxLength=None, *args, **kwargs):
        Entry.__init__(self, myFrame, *args, **kwargs)
        global intCount
        intCount += 1
        self.myFrame   = myFrame
        self.maxLength = maxLength
        
        self.width = kwargs.get('width', 16)

        self.validInt = (self.register(self.ValidateIntInput), '%P', '%S', '%d', '%s')
        self.config(validate='key')
        self.config(validatecommand=self.validInt)
            
    def ChangeState(self, state):
        self['state'] = state
        
    def ValidateIntInput(self, value_if_allowed, text, action, prev_text):
        if len(text) > 1: return True
        if action == '1':
            if self.maxLength == None:
                if len(text) > 1:
                    if re.search(r'[^0-9a-fA-F]', text) == None:
                        return True
                    else:
                        messagebox.showerror('Error', 'Value must be valid hex characters: (0-9, a-f, A-F)')
                        return False
            elif self.maxLength != None:
                if len(prev_text) >= self.maxLength:
                    messagebox.showerror('Error', 'Value must be less than 6 characters.')
                    return False
                else:
                    if re.search(r'[^0-9a-fA-F]', text) == None:
                        return True
                    else:
                        messagebox.showerror('Error', 'Value must be valid hex characters: (0-9, a-f, A-F)')
                        return False
        elif action == "0":
            return True

class IntEntry(Entry):
    def __init__(self, myFrame, maxLength=None, maxValue=None, advance=False, first=False, last=False, *args, **kwargs):
        Entry.__init__(self, myFrame, *args, **kwargs)
        global intCount
        intCount += 1
        self.myFrame   = myFrame
        self.maxLength = maxLength
        self.maxValue  = maxValue
        self.advance   = advance # if max width is reached it will hit 'tab'
        self.first     = first   # if the user presses the left arrow, should it move to the previous. advance must be true
        self.last      = last   # if the user presses the left arrow, should it move to the previous. advance must be true
        
        self.width = kwargs.get('width', 16)
        
        self.validInt = (self.register(self.ValidateIntInput), '%P', '%S', '%d', '%s')
        self.config(validate='key')
        self.config(validatecommand=self.validInt)

        if self.advance:
            self.bind('<KeyRelease>', self.AutoAdvance)
            self.bind('<Right>', self._Right)
            if not self.first:
                self.bind('<Left>', self._Left)
        else:
            if self.last:
                self.bind('<Left>', self._Left)
            
    def GetInt(self, defaultInt:int=0):
        try:
            return int(self.get())
        except:
            return defaultInt

    def Set(self, value:str, defaultValue:int=0):
        self.delete(0, END)
        self.insert(0, value)

    def AutoAdvance(self, event):
        if re.match(r'[0-9]', event.char) and len(self.get()) >= self.cget('width'):
            self.Advance(event)

    def _Right(self, event=None):
        if self.index('insert') == self.index(END):
            self.Advance(event)

    def _Left(self, event=None):
        if self.index('insert') == 0:
            nextWidget = event.widget.tk_focusPrev()
            nextWidget.focus()
            nextWidget.select_range(0, END)

    def Advance(self, event):
        nextWidget = event.widget.tk_focusNext()
        nextWidget.focus()
        nextWidget.select_range(0, END)
            
    def ChangeState(self, state):
        self['state'] = state

    def ValidateIntInput(self, value_if_allowed, text, action, prev_text):
        if len(text) > 1: return True
        if action == '1':
            if len(value_if_allowed) == 1: # allows a negative number
                if text == '-':
                    return True

            if self.maxLength == None and self.maxValue == None:
                if len(text) > 1:
                    try:
                        int(text)
                        return True
                    except:
                        return False
            elif self.maxValue != None:
                
                try:
                    if int(value_if_allowed) <= self.maxValue:
                        return True
                    else:
                        messagebox.showerror('Error', 'Value must be between 0 and {}'.format(self.maxValue))
                        return False
                except:
                    return False
            elif self.maxLength != None:
                if len(prev_text) >= self.maxLength:
                    return False
                else:
                    try:
                        int(text)
                        return True
                    except:
                        return False

            if len(prev_text) >= self.width:
                return False
            if text.isdigit():
                try:
                    int(value_if_allowed)
                    return True
                except:
                    return False
            else:
                return False
        elif action == "0":
            return True

class ScrollFrame(Frame):
    mouseIn = False
    mouseInList = []

    '''     Example
        self.rightScrollFrame = TkinterSaver.ScrollFrame(self, bg='grey55', primaryDirection='horizontal')
        self.rightScrollFrame.pack(side='right', fill='both', expand='yes')
        self.rightPackFrame = self.rightScrollFrame.packFrame
        self.rightPackFrame.bind('<Configure>', None)
        self.rightPackFrame['bg'] = 'grey55'
    '''
    def __init__(self, frame, primaryDirection='vertical', fillWindow=False, printConfig=False, *args, **kwargs):
        Frame.__init__(self, frame, *args, **kwargs)
        self.frame = frame
        self.primaryDirection = primaryDirection
        self.fillWindow = fillWindow

        self.printConfig = printConfig

        self.expandVert = True

        self.configCount = 0 

        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.vScroll = Scrollbar(self, orient='vertical')
        self.vScroll.grid(row=0, column=1, sticky='wens')
        self.hScroll = Scrollbar(self, orient='horizontal')
        self.hScroll.grid(row=1, column=0, sticky='wens')

        self.canvas = Canvas(self, bd=0, highlightthickness=0, 
                                xscrollcommand=self.hScroll.set, 
                                yscrollcommand=self.vScroll.set, 
                                bg=kwargs.get('bg', 'grey55'))

        self.canvas.grid(row=0, column=0, sticky='wens')
        self.canvas.bind('<Enter>', self.MouseIn)
        self.canvas.bind('<Leave>', self.MouseOut)
        self.vScroll.config(command=self.canvas.yview)
        self.hScroll.config(command=self.canvas.xview)

        self.packFrame = Frame(self.canvas)
        self.packWindow = self.canvas.create_window(0,0, window=self.packFrame, anchor='nw')

        self.CreateConfigureEvent()

    def CreateConfigureEvent(self):
        if self.fillWindow:
            self.configureEvent = self.canvas.bind('<Configure>', self.ConfigureFill)
        else:
            self.configureEvent = self.canvas.bind('<Configure>', self.ConfigureCanvas)

    def AutoFitHeight(self, maxHeight=350):
        self.frame.update_idletasks()
        height = self.packFrame.winfo_reqheight()

        if height > maxHeight: height = maxHeight
        self.canvas.config(height=height)

    def MouseIn(self, event=None):
        self.mouseIn = True
        ScrollFrame.mouseInList.append(self)

        if self.primaryDirection == 'vertical':
            ScrollFrame.mouseInList[-1].canvas.bind_all('<MouseWheel>', self.VerticalScroll)
            ScrollFrame.mouseInList[-1].canvas.bind_all('<Control-MouseWheel>', self.HorizontalScroll)
        elif self.primaryDirection == 'horizontal':
            ScrollFrame.mouseInList[-1].canvas.bind_all('<MouseWheel>', self.HorizontalScroll)
            ScrollFrame.mouseInList[-1].canvas.bind_all('<Control-MouseWheel>', self.VerticalScroll)

    def MouseOut(self, event=None):

        self.mouseIn = False
        ScrollFrame.mouseInList[-1].unbind('<MouseWheel>')
        ScrollFrame.mouseInList[-1].unbind('<Control-MouseWheel>')
        ScrollFrame.mouseInList.pop(-1)
        if ScrollFrame.mouseInList != []:
            ScrollFrame.mouseInList[-1].MouseIn()
            '''
            if ScrollFrame.mouseInList[-1].primaryDirection == 'vertical':
                ScrollFrame.mouseInList[-1].canvas.bind_all('<MouseWheel>', ScrollFrame.mouseInList[-1].VerticalScroll)
                ScrollFrame.mouseInList[-1].canvas.bind_all('<Control-MouseWheel>', ScrollFrame.mouseInList[-1].HorizontalScroll)
            elif ScrollFrame.mouseInList[-1].primaryDirection == 'horizontal':
                ScrollFrame.mouseInList[-1].canvas.bind_all('<MouseWheel>', ScrollFrame.mouseInList[-1].HorizontalScroll)
                ScrollFrame.mouseInList[-1].canvas.bind_all('<Control-MouseWheel>', ScrollFrame.mouseInList[-1].VerticalScroll)
            '''

    def VerticalScroll(self, event=None):
        if self.vScroll.get() == (0.0, 1.0) or not self.mouseIn: return
        self.canvas.yview_scroll(int(event.delta/120)*-1, 'units')

    def HorizontalScroll(self, event=None):
        if self.hScroll.get() == (0.0, 1.0) or not self.mouseIn: return
        self.canvas.xview_scroll(int(event.delta/120)*-1, 'units')

    def PassFunc(self, event=None): pass

    def ClearControls_Grid(self):
        for child in self.packFrame.winfo_children():
            child:Frame
            child.grid_forget()
            child.destroy()
        self.ConfigureCanvas()
        
    def ClearControls_Pack(self):
        for child in self.packFrame.winfo_children():
            child:Frame
            child.pack_forget()
            child.destroy()
        self.ConfigureCanvas()

    def ConfigureCanvas(self, event=None, overrideWidth:int=-1):
        
        '''
        if self.printConfig: print(self.configureEvent)
        

        self.canvas.bind('<Configure>', None)
        self.canvas.update_idletasks()
        masterHeight = self.frame.winfo_height()
        pFheight = self.packFrame.winfo_height()

        if self.printConfig: print('{} ::: {}'.format(masterHeight, pFheight))

        self.canvas.config(height=pFheight)
        self.canvas.update_idletasks()
        
        self.canvas.bind('<Configure>', self.ConfigureCanvas)
        print(self)
        '''
        

        self.configCount += 1
        #print(self.configCount )
        scrollRegion = self.canvas['scrollregion'].split(' ')
        #print('{: >11.11} : {} ::: {}'.format(time.time(), scrollRegion, self.canvas.winfo_reqheight()))
        try:
            horzRegion = int(scrollRegion[2])
            vertRegion = int(scrollRegion[3])
        except IndexError:
            horzRegion = None
            vertRegion = None
        if self.packFrame.winfo_reqheight() != vertRegion or self.packFrame.winfo_reqwidth() != horzRegion:
            self.packFrame.update_idletasks()
            size = (2, self.packFrame.winfo_reqheight())
            self.canvas.config(scrollregion=(0,0,size[0], size[1]))

        if overrideWidth > -1:
            self.canvas.config(width=overrideWidth)
            self.config(width=overrideWidth)

        #self.canvas.itemconfig(self.packWindow, height=self.frame.winfo_height())
        #self.packFrame.config(height=self.frame.winfo_height())
        #self.canvas.config(height=self.frame.winfo_height())
   
    def ConfigureFill(self, event=None):
        #if event == None: return
        
        self.canvas.itemconfig(self.packWindow, width=event.width)
        #self.canvas.itemconfig(self.packWindow, height=event.height)
        self.ConfigureCanvas()

class FrameScroll: # do not use. Depreciated: Use ScrollFrame Instead
    def __init__(self, frame, eleHeight=10, myTag='frameScroll', verticalScroll=True, horizontalScroll=False, **canvasKwargs):
        self.frame = frame
        self.eleHeight = eleHeight
        self.myTag = myTag
        
        self.frameScrollFrame = Frame(self.frame, bg='grey55')
        
        self.height = 0
        
        self.canvas = Canvas(self.frameScrollFrame, bg='grey55', **canvasKwargs)
        self.canvas.grid(row=0, column=0, padx=1, pady=1, sticky='wens')
        if verticalScroll:
            self.vertScroll = Scrollbar(self.frameScrollFrame, orient='vertical', command=self.canvas.yview)
            self.vertScroll.grid(row=0, column=1, sticky='wens')
            self.canvas.configure(yscrollcommand=self.vertScroll.set)
        if horizontalScroll:
            self.horzScroll = Scrollbar(self.frameScrollFrame, orient='horizontal', command=self.canvas.xview)
            self.horzScroll.grid(row=1, column=0, sticky='wens')
            self.canvas.configure(xscrollcommand=self.horzScroll.set)
        
        self.canvas.bind('<Button-1>', self.GrabFocus)
        #self.canvas.bind('<Enter>', self.GrabFocus)
        self.canvas.bind('<MouseWheel>', self.ScrollCanvas)
        self.canvas.bind('<Configure>', self.ResizeFrame)
        self.frameScrollFrame.columnconfigure(0, weight=1)
        self.frameScrollFrame.rowconfigure(0, weight=1)
        
        self.packFrame = Frame(self.canvas, bg=RGB(0, 0, 175))
        self.canvas.create_window((1,1), window=self.packFrame, anchor='nw', tags=self.myTag)
        
    def ResizeFrame(self, event):
        self.canvas.itemconfig(self.myTag, width=event.width)
        
        
    def firstPack(self, **kwargs):
        self.frameScrollFrame.pack(kwargs)
        self.ConfigureCanvas()
        
    def firstGrid(self, **kwargs):
        self.frameScrollFrame.grid(**kwargs)
        self.ConfigureCanvas()
        
    def pack(self, **kwargs):
        self.packFrame.pack(**kwargs)
        self.ConfigureCanvas()
        
    def grid(self, **kwargs):
        self.packFrame.grid(**kwargs)
        self.ConfigureCanvas()
    
        
    def ScrollCanvas(self, event=None):
        direction = 0 
        if event.delta == 120:
            direction = -1
        elif event.delta == -120:
            direction = 1
        self.canvas.yview_scroll(direction, 'units')

    def GrabFocus(self, event=None):
        self.canvas.focus_force()
        
    def ConfigureCanvas(self, event=None):
        self.packFrame.update_idletasks()
        bounds = self.canvas.bbox('all')
        #bounds = (bounds[0], bounds[1], self.packFrame.winfo_reqwidth(), bounds[3])
        #self.canvas.itemconfig(self.myTag, width=bounds[2])
        self.canvas.configure(scrollregion=(bounds))
        
        #self.packFrame.update_idletasks()

        newWidth = 435 + self.canvas.bbox('all')[2]

        #if newWidth <= self.frame.winfo_screenwidth() - 435:
        #    self.frame.geometry('{}x{}'.format(newWidth, self.frame.winfo_height()))
        self.canvas.xview_moveto(1.0)

class RefreshButton(Label):
    def __init__(self, frame, *args, **kwargs):
        command = kwargs.pop('command', self.passFunc)
        icon = kwargs.pop('pressed', u'\u21B7')
        pressed = kwargs.pop('pressed', u'\u21BB')

        Label.__init__(self, frame, *args, **kwargs)
        #cnf = {**cnf, **kwargs}
        self.kwargs = kwargs
        

        if 'relief' not in kwargs:
            kwargs['relief'] = 'raised'
        if 'text' not in kwargs:
            kwargs['text'] = icon
        if 'font' not in kwargs:
            kwargs['font'] = ('', 12)
        

        self.config(**kwargs)
        self.bind('<Enter>', self._mousein)
        self.bind('<Leave>', self._mouseout)

        self.kwargs['command'] = command
        self.kwargs['pressed'] = pressed

    def passFunc(self):
        pass

    def _mousein(self, event):
        self.bind('<Button-1>', self._buttonpressed)

    def _mouseout(self, event):
        self.unbind('<Button-1>')
        self.unbind('<ButtonRelease-1>')

        self.config(relief=self.kwargs['relief'], text=self.kwargs['text'])

    def _buttonpressed(self, event):
        self.config(relief='sunken')
        self.bind('<ButtonRelease-1>', self._buttonrelease)
        self.config(text=self.kwargs['pressed'])

    def _buttonrelease(self, event):
        self.config(relief=self.kwargs['relief'])
        self.kwargs['command']()
        self.config(text=self.kwargs['text'])

class LabelValue(Frame):
    '''
        A frame containing two labels. 
        First label will be a description
        Second label will be a value
    '''
    def __init__(self, frame, label, value, *args, **kwargs):
        Frame.__init__(self, frame, *args, **kwargs)
        self.label = Label(self, text=label)
        self.label.pack(side='left', **packKwargs)


        self.value = Label(self, text=value)
        self.value.pack(side='left', **packKwargs)

    def set(self, newVal):
        self.value.config(text=newVal)

class StatusCircle(Frame):
    def __init__(self, frame, text = "", size = 50, *args, **kwargs):
        Frame.__init__(self, frame, *args, **kwargs)
        self.frame = frame
        self.text  = text
        self.size  = size

        self.label = Label(self, text = self.text)
        self.label.pack(side = "left", **packKwargs)

        self.canvas = Canvas(self, width = self.size, height = self.size)
        self.canvas.pack(side = "left", **packKwargs)

        buffer = self.size / 10
        self.status = "neutral"
        self.statusCircle = self.canvas.create_oval(buffer, buffer, self.size - buffer, self.size - buffer,
            outline = "", fill = "grey55")

    def Good(self):
        self.status = "good"
        self.canvas.itemconfig(self.statusCircle, fill = RGB(0, 150, 0))

    def Bad(self):
        self.status = "bad"
        self.canvas.itemconfig(self.statusCircle, fill = RGB(150, 0, 0))

    def Pending(self):
        self.status = "pending"
        self.canvas.itemconfig(self.statusCircle, fill = RGB(200, 200, 0))

    def Neutral(self):
        self.status = "neutral"
        self.canvas.itemconfig(self.statusCircle, fill = "grey55")

    def Reset(self): # calls neutral, for ease of use.
        self.Neutral()

class ReadWriteEntry(Frame): 
    def __init__(self, frame:Tk, header:str="Parameter", readFunc:Callable=None, writeFunc:Callable=None, *args, **kwargs):
        """Creates a frame with a header. Includes an entry field for read and write values   

        Args:
            frame (Tk): Parent frame/master to pack into
            header (str, optional): Parmeter name to appear in the header label. Defaults to "Parameter".
            readFunc (Callable, optional): Function to call when the read button is clicked. Defaults to None.
            writeFunc (Callable, optional): Function to call when the write button is clicked. Defaults to None.
        """        
        Frame.__init__(self, frame, *args, **kwargs)
        self.readFunc = readFunc
        self.writeFunc = writeFunc

        self.paramLabel = Label(self, text=header, relief = 'sunken')
        self.paramLabel.grid(row=0, column = 0, columnspan = 4, **gridKwargs)

        self.readButton = Button(self, text='Read', command=self.ReadButton_Click, width=5)
        self.readButton.grid(row=1, column=0, **gridKwargs)
        self.writeButton = Button(self, text='Write', command=self.WriteButton_Click, width=5)
        self.writeButton.grid(row=1, column=1, **gridKwargs)

        self.valueEntry = Entry(self)
        self.valueEntry.grid(row=1, column=2, **gridKwargs)

        self.entryWidget = self.valueEntry # used for child class. Makes it so lock/unlock works without overriding

        self.columnconfigure(2, weight=1)

        #self.frameCombo = ttk.Combobox(self, values = self.frameList, width = 15, name='breakerFrameCombo')
        #self.frameCombo.grid(row=1, column=3, **gridKwargs)

    def Get(self) -> str:
        return self.entryWidget.get()
    
    def Set(self, text:str):
        self.valueEntry.delete(0, END)
        self.valueEntry.insert(0, text)

    def Lock(self):
        """Disable all controls"""        
        self.readButton.config(state="disabled")
        self.writeButton.config(state="disabled")
        self.entryWidget.config(state="disabled")

    def Unlock(self):
        """Enable all controls"""      
        self.readButton.config(state="normal")
        self.writeButton.config(state="normal")
        self.entryWidget.config(state="normal")

    def MakeReadOnly(self):
        """Removes the write button and repacks controls"""      
        self.columnconfigure(2, weight=0)
        self.columnconfigure(1, weight=1)
        self.writeButton.grid_forget()
        self.entryWidget.grid_forget()
        self.entryWidget.grid(row=1, column=1, **gridKwargs)

    def MakeWriteableOnly(self):
        """Adds the write button and repacks controls"""  
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        self.entryWidget.grid_forget()
        self.entryWidget.grid(row=1, column=2, **gridKwargs)

        self.writeButton.grid_forget()
        self.writeButton.grid(row=1, column=1, **gridKwargs)

    def StartRead(self):
        self.Lock()
        self.readButton.WorkStart()

    def ParseRead(self, success:bool) -> bool:
        self.Unlock()
        self.readButton.ParseBool(success)
        return success
    
    def StartWrite(self):
        self.Lock()
        self.writeButton.WorkStart()

    def ParseWrite(self, success:bool) -> bool:
        self.Unlock()
        self.writeButton.ParseBool(success)
        return success
        
    def ReadButton_Click(self):
        if self.readFunc is None:
            return

        self.readFunc()

    def WriteButton_Click(self):
        if self.writeFunc is None:
            return
        
        self.writeFunc()

class ReadWriteDropdown(ReadWriteEntry):
    def __init__(self, frame:Tk, values:List[str], header:str="Parameter", readFunc:Callable=None, writeFunc:Callable=None, *args, **kwargs):
        ReadWriteEntry.__init__(self, frame, header, readFunc, writeFunc, *args, **kwargs)
        self.values = values
        self.valueEntry.grid_forget()

        self.valueCombo = ttk.Combobox(self, values = self.values)
        self.valueCombo.grid(row=1, column=3, **gridKwargs)

        self.entryWidget = self.valueCombo

    def UpdateValues(self, newValues:List[str]):
        self.values = newValues
        self.valueCombo.config(values=newValues)
    
    def Set(self, text:str):
        self.valueCombo.set(text)

class ToggleButton(Frame):
    def __init__(self, parentFrame, text="", activeColor="lightgreen", unactiveColor="grey95", holdingColor="yellow", *args, **kwargs):
        Frame.__init__(self, parentFrame, *args, **kwargs)

        self.buttonActive = False
        self.leaveLabelBind = None
        self.leaveFrameBind = None

        self.activeColor = activeColor
        self.unactiveColor = unactiveColor
        self.holdingColor = holdingColor

        self.config(relief="raised", bd=2)

        self.label = Label(self, text=text)
        self.label.pack(fill="both", expand=True)
        self.label.bind("<ButtonPress-1>", self.Handle_MouseDown)
        self.bind("<ButtonPress-1>", self.Handle_MouseDown)

        self.label.bind("<ButtonRelease-1>", self.Handle_MouseUp)
        self.bind("<ButtonRelease-1>", self.Handle_MouseUp)

        self.pressedEvents = []
        self.releaseEvents = []

    def SubscribePressed(self, func:callable):
        self.pressedEvents.append(func)

    def SubscribeRelseased(self, func:callable):
        self.releaseEvents.append(func)
            
    def Handle_MouseDown(self, event=None):
        self.config(bg=self.holdingColor, relief="flat")
        self.label.config(bg=self.holdingColor)

        self.leaveFrameBind = self.bind("<Leave>", self.Handle_Leave)
        self.leaveLabelBind = self.label.bind("<Leave>", self.Handle_Leave)

    def UnbindLeave(self):
        self.unbind("<Leave>", self.leaveFrameBind)
        self.label.unbind("<Leave>", self.leaveLabelBind)

        self.leaveFrameBind = None
        self.leaveLabelBind = None


    def Handle_MouseUp(self, event=None):
        if self.leaveLabelBind is None: # Will be true if mouse left the control.
            return
        
        self.UnbindLeave()

        if self.buttonActive:
            self.buttonActive = False

            self.config(bg=self.unactiveColor)
            self.label.config(bg=self.unactiveColor)
            self.config(relief="raised", bd=2)

            for func in self.releaseEvents:
                func()

        else:
            self.buttonActive = True

            self.config(bg=self.activeColor)
            self.label.config(bg=self.activeColor)
            self.config(relief="sunken", bd=2)

            for func in self.pressedEvents:
                func()

    def Handle_Leave(self, event=None):
        self.UnbindLeave()

        if self.buttonActive:
            self.config(bg=self.activeColor, relief="sunken")
            self.label.config(bg=self.activeColor)
        else:
            self.config(bg=self.unactiveColor, relief="raised")
            self.label.config(bg=self.unactiveColor)

class AsyncButton(Button): # Unfiished. Unsure if this makes sense to make
    def __init__(self, frame, callbackFunc:callable, *args, **kwargs):
        Button.__init__(self, frame, *args, **kwargs)

        self.callBack = callbackFunc

        self.bind("<Button>", self.__click__)

        #self.config(command=self.__click__)

    def __click__(self, event=None):
        print("Clicked")

class LoadButton(Button):
    def __init__(self, parent:Frame, loadChars:List[str]=None, *args, **kwargs):
        Button.__init__(self, parent, *args, **kwargs)
        if loadChars is None:
            loadChars = [".", "..", "..."]
        self.loadChars = loadChars

        self.charCount = len(self.loadChars)

        self.storedText = ""
        self.loadIndex = 0
        self.keepLoading = True

    def UseCircleLoadingIcons(self):
        self.loadChars = [
            u"\u25CB",
            u"\u25D4",
            u"\u25D1",
            u"\u25D5",
            u"\u263B",
        ]
        self.charCount = len(self.loadChars)

    def StartLoading(self):
        self.storedText = self.cget("text")
        self.config(state="disabled")

        self.LoadLoop()

    def StopLoading(self):
        self.keepLoading = False
        

    def LoadLoop(self):
        self.config(text=self.loadChars[self.loadIndex])

        self.loadIndex += 1
        self.loadIndex = self.loadIndex % self.charCount

        if self.keepLoading:
            self.after(250, self.LoadLoop)
        else:
            self.config(text=self.storedText, state="normal")

class ToolTip:
    def __init__(self, control:Tk, text:str, waitTime:int=500, wrapLength=180):
        self.control = control
        self.text = text
        self.waitTime = waitTime     # ms
        self.wrapLength = wrapLength # pixels

        self.control.bind("<Enter>", self.Handle_Enter)
        self.control.bind("<Leave>", self.Handle_Leave)
        self.control.bind("<ButtonPress>", self.Handle_Leave)

        self.afterID = None
        self.popUp = None

    def Handle_Enter(self, event=None):
        if self.popUp:
            return
        
        self.Handle_Leave(event)

        self.control.after(self.waitTime, self.ShowTip)

    def Handle_Leave(self, event=None):
        afterID = self.afterID
        self.afterID = None
        
        if afterID:
            self.control.after_cancel(afterID)

        self.HideTip()

    def ShowTip(self):
        x = 0
        y = 0

        x, y, cx, cy = self.control.bbox("insert")
        x += self.control.winfo_rootx() + 25
        y += self.control.winfo_rooty() + 20

        self.popUp = Toplevel(self.control)
        self.popUp.wm_overrideredirect(True)
        self.popUp.wm_geometry(f"+{x}+{y}")

        label = Label(self.popUp, text=self.text, justify="left", relief="solid", bd=2, 
                      wraplength=self.wrapLength)
        label.pack(ipadx=1)

    def HideTip(self):
        popup = self.popUp
        self.popUp = None
        if popup:
            popup.destroy()
        
class ToggleElement:
    def __init__(self, parent:Tk):
        self.parent = parent

        self.isSelected = False
        self.childControls:Dict[Tk, Tuple[str, str]] = {} # key will be control. First tuple Item will be select color, second tuple is deselect color

        self.ClickEvent:List[Callable[[Tk, bool], None]] = []

    def Subscribe(self, func:Callable[[Tk, bool], None]):
        self.ClickEvent.append(func)

    def AddControl(self, control:Tk, selectColor:str=None, deselectColor:str=None):
        """Add control that will bind to <Button-1> and change format based on click status.

        Args:
            control (Tk): Control to format and add click event to. 
            selectColor (str): Background color to change control when selected
            deselectColor (str, optional): Background color to change control when selected. Defaults to color of control when function is called.
        """
        if selectColor is None:
            selectColor = RGB(150, 230, 250)
        if deselectColor is None:
            deselectColor = control.cget("bg")
        self.childControls[control] = (selectColor, deselectColor)
        control.bind("<Button-1>", self.ToggleControl)

    def ToggleControl(self, event=None):
        if self.isSelected:
            self.DeselectControl()
        else:
            self.SelectControl()

    def FormatControls(self):
        selectIndex = 0 if self.isSelected else 1
        relief = "sunken" if self.isSelected else "raised"

        for control, colorTuple in self.childControls.items():
            cColor = colorTuple[selectIndex]
            control.config(bg=cColor)

        self.parent.config(relief=relief, bd=2)


    def SelectControl(self):
        self.isSelected = True
        self.FormatControls()

        for func in self.ClickEvent:
            func(self.parent, self.isSelected)

    def DeselectControl(self):
        self.isSelected = False
        self.FormatControls()

        for func in self.ClickEvent:
            func(self.parent, self.isSelected)

def VerifyIpAddress(entertedIpAdress:str) -> bool:
    """Determine if enteredIpAddress is in the correct format for an IP address

    Args:
        entertedIpAdress (str): ip address as a string

    Returns:
        bool: is the ip address formmated correctly.
    """    
    octetFind = re.findall(r"\d+", entertedIpAdress)

    if len(octetFind) != 4:
        return False

    intList = [int(x) for x in octetFind]
    return all(x >= 0 and x <255 for x in intList)

def VerifyIntEntry(entryControl:Entry, defaultValue:int=-1) -> Tuple[int, bool]:
    """Try to convert a user input from an Entry control to an Integer. 

    Args:
        entryControl (Entry): Control with value to convert to int
        defaultValue (int, optional): Value to use if conversion fails. Defaults to -1.

    Returns:
        Tuple[int, bool]: Converted value or default on failure ::: Was value succesffully converted to integer.
    """    
    rawValue = entryControl.get()

    try:
        value = int(rawValue)
    except:
        return defaultValue, False
    
    return value, True

def CheckFileExists(filePath:str) -> bool:
    """Checks if given path exists

    Args:
        filePath (str): Relative or absolute path to file to check

    Returns:
        bool: True if file exists
    """    
    return os.path.exists(filePath)

def AddDict(myLabel, myEle):
    myDict[myLabel] = myEle

def CheckForTkinterConfigFolder() -> str:
    """Find path where python is installed. Check for or add Tkinter_Config folder.

    Returns:
        str: path to Tkinter_Config folder to save restore files.
    """    
    path = os.path.join(os.path.split(sys.executable)[0], 'Tkinter_Config')
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception as e:
            print('Failed to create directory to save config files. Will save in current working directly: {}'.format(e))

    return path

def PrepSaveFile(outFileName) -> str:
    """Check Tkinter_Config folder exists. Create if not. Combine passed in outFileName with config folder. 

    Args:
        outFileName (_type_): File name for config file

    Returns:
        str: Absoluate path of file name. None if can't create output directory.
    """    
    path = CheckForTkinterConfigFolder()

    if os.access(path, os.R_OK):
        outFileName = os.path.join(path, outFileName)
    else:
        path = os.path.join(os.getcwd(), 'Tkinter_Config')
        outFileName = os.path.join(path, outFileName)
        if not os.path.isdir(path):
            try: 
                os.makedirs(path)
            except Exception as e:
                print('Failed to create tkinter config folder. Check permissions. Will not be able to save config file: {}'.format(e))
                return None
            
    return outFileName

def SaveElements(outFileName:str, eleDict:Dict[Any, Any], pathName:str=None):
    """Converts eleDict to json string and saves to config file. 

    Args:
        outFileName (str): Name of the config file. Will use default tkinter_config folder if pathName is omitted.
        eleDict (_type_): Dictionary of values to save as json string
        pathName (_type_, optional): Path name to use if not default. Defaults to None. TODO: Implement this
    """    
    outFileName = PrepSaveFile(outFileName)
    if outFileName is None:
        return
    
    #outFileName = os.path.join(temp, outFileName)
    outFile = open(outFileName, "w")
    tempString = json.dumps(eleDict)
    outFile.write(tempString)
    outFile.close()

def GetConfigInfoFromFile(configFileName) -> str:
    """Attept to get file from ../Tkinter_Config/{configFileName} and return text as a string

    Args:
        configFileName (str): Name of config file in ../Tkinter_Config. Include extension. 

    Returns:
        str: Text of file if found. None if not.
    """

    fullFileName = PrepSaveFile(configFileName)

    if not os.path.isfile(fullFileName):
        return None

    readText = open(fullFileName, "r")

    return readText.readline().strip()

def GetElements(myFrame, firstCall = True, otherDict=None, myDict={}):
    ''' will loop through every widget in passed in myFrame'''
    '''can manually set output file name with outFileName var
    temp = os.path.join('C:\\', 'Python37-32', 'Tkinter_Config')
    if not os.path.isdir(temp):
        os.makedirs(temp)
    '''
    if firstCall:
        myDict = {}
        
    for item in myFrame.winfo_children():
        if item.winfo_class() == "Frame":             #Frame
            GetElements(item, False, myDict=myDict)
        elif item.winfo_class() == "Radiobutton":    #Radiobutton
            try:
                myLabel = str(item.cget("variable"))
                myDict[myLabel] = item.getvar(item.cget("variable"))
            except Exception as e:
                print ('GetElements: Radiobutton Save Error:\n{}'.format(e))
        elif item.winfo_class() == "Entry" or item.winfo_class() == 'TCombobox':         #Entry
            try:
                myLabel = re.sub(r".*\.","", str(item))
                myDict[myLabel] = item.get()
            except Exception as e:
                print ('GetElements: Entry Save Error:\n{}'.format(e))
        elif item.winfo_class() == "Menubutton":     #Menubutton
            try:
                myLabel = item.cget("textvariable")
                myDict[myLabel] = item.getvar(item.cget("textvariable"))
            except Exception as e:
                print ('GetElements: Menubutton Save Error:\n{}'.format(e))
        elif item.winfo_class() == "Checkbutton":     #Checkbutton
            try:
                myLabel = str(item.cget("variable"))
                myDict[myLabel] = int(item.getvar(item.cget("variable")))
            except Exception as e:
                print ('GetElements: Checkbutton Save Error:\n{}'.format(e))
        else:
            pass
            #print "Other Widget = " + item.winfo_class()
        prevEle = item.winfo_class()
    if otherDict != None:
        AddDict('otherDict', otherDict)
    
    if firstCall:
        '''
        outFile = open(outFileName, "w")

        tempString = json.dumps(myDict)
        outFile.write(tempString)
        outFile.close()
        '''

        return myDict
    
def RestoreTkinter(myFrame, outFileName="TkinterRemember.cfg", otherDict=None, displayErrors=False):
    #outFileName = os.path.join('C:\\', 'Python37-32', 'Tkinter_Config', outFileName)
    path = os.path.join(os.path.split(sys.executable)[0], 'Tkinter_Config')
    if os.access(path, os.R_OK):
        outFileName = os.path.join(path, outFileName)
    else:
        outFileName = os.path.join(os.getcwd(), 'Tkinter_Config', outFileName)

    if os.path.isfile(outFileName):
        with open(outFileName, "r") as inFile:
            tempString = inFile.readline().strip()
        try:
            readJson = json.loads(tempString) #, encoding='utf-8')
        except ValueError:
            return
        except TypeError as e:
            return
        tempString = ""
        returnDict = readJson
        try:
            readJson = readJson['tkinter']
        except KeyError:
            pass
        else:
            InitializeElements(myFrame, readJson, displayErrors=displayErrors)
    else:
        returnDict = {}

    return returnDict

def InitializeElements(myFrame, myDict, firstCall=True, displayErrors=False):
    for item in myFrame.winfo_children():
        #print(item.winfo_class())
        if item.winfo_class() == "Frame":            #Frame
            InitializeElements(item, myDict, False)
            
        elif item.winfo_class() == "Radiobutton":    #Radiobutton
            myLabel = str(item.cget("variable"))
            if re.match('ignore', str(myLabel), re.IGNORECASE): continue
            try:
                if myDict[myLabel] == item["value"]:
                    item.invoke()
            except:
                pass
                
                
        elif item.winfo_class() == "Entry":            #Entry
            myLabel = re.sub(r".*\.","", str(item))
            if re.match('ignore', str(myLabel), re.IGNORECASE): continue
            try:
                if item["state"] == "readonly":
                    item["state"] = "normal"
                    if len(item.get()) > 0: item.delete(0, END)
                    item.insert(0, myDict[myLabel])
                    item["state"] = "readonly"
                else:
                    if len(item.get()) > 0: item.delete(0, END)
                    item.insert(0, myDict[myLabel])
                    #print '{} : {} : {}'.format(item, myLabel, readJson[myLabel])
            except Exception as e:
                pass
                
        elif item.winfo_class() == 'TCombobox':
            myLabel = str(item).split('.')[-1]
            if re.match('ignore', str(myLabel), re.IGNORECASE): continue
            try:
                if item["state"] == "readonly":
                    item["state"] = "normal"
                    if len(item.get()) > 0: item.delete(0, END)
                    item.insert(myDict[myLabel])
                    item["state"] = "readonly"
                else:
                    if len(item.get()) > 0: item.delete(0, END)
                    item.set(myDict[myLabel])
                    #print '{} : {} : {}'.format(item, myLabel, readJson[myLabel])
            except Exception as e:
                pass

                
        elif item.winfo_class() == "Menubutton":    #Menubutton
            myLabel = item.cget("textvariable")
            if re.match('ignore', str(myLabel), re.IGNORECASE): continue
            try:
                item.setvar(item.cget("textvariable"), str(myDict[myLabel]))
            except:
                if displayErrors: print ("Failed to get %s information" % myLabel)
                
                
        elif item.winfo_class() == "Checkbutton":    #Checkbutton
            myLabel = item.cget("variable")
            if re.match('ignore', str(myLabel), re.IGNORECASE): continue
            try:
                if myDict[str(myLabel)] != item.getvar(myLabel):
                    item.invoke()
                
            except Exception as e:
                if displayErrors: print ("Failed to get %s information" % myLabel)

        


        else:
            pass

            
if __name__ == '__main__': 
    mw = Tk()

    b = AsyncButton(mw, None, text="Click Me")
    b.pack()

    mw.mainloop()
    