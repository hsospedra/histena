#!/usr/bin/python3

import tkinter as tk
import tkinter.ttk as ttk
import sqlite3 as sq 

from tkinter import messagebox 

from time import sleep

import tooltip
from tooltip import *
import dbAnnot
from dbAnnot import *
from PersonUI import *
from LocationUI import *
from KeywordUI import *
from threading import Timer
import functools

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.function   = function
        self.interval   = interval
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

class NewWork(tk.Toplevel):   

    # signal/callback to update person entries
    signalAdded = None
        
    def __init__(self, parent):
        super().__init__(parent)
        self.geometry("400x300+800+300")
        self.title("add new series")

        frame = tk.Frame(self)
        frame.pack(fill=tk.X)

        lbl = tk.Label(frame, text="Title", width=10)
        lbl.pack(side=tk.LEFT, padx=5, pady=5)
        
        self._title = tk.StringVar()
        self._title.set("")
        self._title.trace_add("write", self.enableEntry)
        
        entry = tk.Entry(frame, textvariable=self._title)
        entry.pack(fill=tk.X, padx=5, expand=True)

        frame = tk.Frame(self)
        frame.pack(fill=tk.X)

        lbl = tk.Label(frame, text="abbreviation", width=10)
        lbl.pack(side=tk.LEFT, padx=5, pady=5)

        self._abbrev = tk.StringVar()
        entry = tk.Entry(frame, textvariable=self._abbrev)
        entry.pack(fill=tk.X, padx=5, expand=True)

        frame = tk.Frame(self)
        frame.pack(fill=tk.X)

        lbl = tk.Label(frame, text="Description", width=10)
        lbl.pack(side=tk.LEFT, anchor=tk.N, padx=5, pady=5)

        self._description = tk.Text(frame, width=20, height=10)
        self._description.pack(fill=tk.BOTH, pady=5, padx=5, expand=True)

        frame = tk.Frame(self, padx=5, pady=5, borderwidth=1)
        frame.pack(fill=tk.X, expand=True)
        cancelButton = tk.Button(frame, text ="cancel",command=self.cancel)
        cancelButton.pack(side=tk.RIGHT)
        self._okButton = tk.Button(frame, text ="ok",command=self.ok)
        self._okButton.pack(side=tk.RIGHT)
        self._okButton.config(state=tk.DISABLED)

    def cancel(self):
        print("oeoeoe")
        self.destroy();

    def ok(self):
        sql = 'INSERT INTO works (title,description,abbreviation) VALUES (?,?,?)'
        values = (self._title.get(), self._description.get(1.0,tk.END), self._abbrev.get())
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        # get work id 
        records = dbAnnot.db.execute("SELECT last_insert_rowid()")
        self.signalAdded(records.fetchone()[0], self._title.get())
        self.destroy()

    def enableEntry(self, var, index, mode):
        if self._title.get()=="":
            self._okButton.config(state=tk.DISABLED)
        else:
            self._okButton.config(state=tk.NORMAL)

    # callbacks
def compareByDate(item):
    
    # order of comparison: state, year, month, day
    # state = 0 for untagged, 1 for standard, 2 for no date

    state = '1'
    sep = '_id_'
    date,idDoc = item.split(sep,1)

    # already tagged
    if "untagged" in idDoc:
        state = '0'

    if date == "undated":
        return ("2", "0","0","0")

    day,month,year = date.split("/")
    return(state,year,month,day)

class UI(object):

    _works = []
    _docs = []
    _typeSelected = "no selection"
    _annotations = []

    # constructor
    def __init__(self):
        self._window = tk.Tk()

        self._window.title("text annotation")   
        self._window.geometry("1800x1000")
        self._tabs = ttk.Notebook(self._window)    
        
        self._window.bind("<KeyPress>", self.keyDown)

        self.createDocsTab();
        self.createCiteFrame();
        self.createAddSourceFrame();
        
        self._tabs.pack(expand=1, fill="both")

    def keyDown(self, key):
    
        # location
        if key.char == "l":
            self._typeSelected = "location"
            self.addAnnotation()
            return
        # person    
        if key.char == "p":    
            self._typeSelected = "person"
            self.addAnnotation()
            return
        # keyword
        if key.char == "k":
            self._typeSelected = "keyword"
            self.addAnnotation()
            return


    def selectWork(self, event):
        self._docs = {}
        # pick value at index of mouse click
        if len(self._worksList.curselection())==0:
            return

        index = self._worksList.curselection()[0]
        workId = self._works[self._worksList.get(index)]
        self._docsList.delete(0, tk.END)
        records = dbAnnot.db.execute("SELECT * from docs where id_work="+str(workId))

        listValues = []

        sep = '_id_'

        # docs are sorted by date
        for row in records.fetchall():
            date = row[3]
            if date==None or date=="":
                date=  "undated"
                
            # we need to do this to avoid losing track of id when sorting them
            date = date + sep+str(row[0])

            # add warning if doc has no annotations
            annotDoc = dbAnnot.db.execute("SELECT * from annotations where id_doc="+str(row[0]))
            if len(annotDoc.fetchall())==0:
                date = date + "untagged*"

            listValues.append(date)

        listValues.sort(key=compareByDate)

        index = 1       
        for value in listValues:
            idValue = value.split(sep, 1)[1] 
            date = value.split(sep, 1)[0]

            fullTitle = str(index) + ": " + date 
            
            # untagged, add a visible mark
            if "untagged" in value:
                fullTitle = "*** "+fullTitle
                idValue = idValue[0:idValue.find("untagged")]
                
            self._docs[fullTitle] = idValue
            self._docsList.insert(index, fullTitle)
            index += 1

        # clean doc
        self.clearDoc()

    def clearDoc(self):
        self.clearAnnotation()
        
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)

        self._titleInfo.set("-")
        self._refInfo.set("-")
        self._dateInfo.set("-")
        self._authorInfo.set("-")
        self._locationInfo.set("-")

    def selectDoc(self, event):
        #value = docsList.get(docsList.curselection())
        # starts at 0
        self.clearAnnotation()
    
        if len(self._docsList.curselection())==0:
            return

        # value = int(docsList.get(tk.ANCHOR)) 
        index = self._docsList.curselection()[0]
        docId = self._docs[self._docsList.get(index)]

        records = dbAnnot.db.execute("SELECT * from docs where ID="+str(docId))
        doc = records.fetchone()

        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.INSERT, doc[4]) 
        self._text.config(state=tk.DISABLED)

        self._titleInfo.set(doc[2])
        self._dateInfo.set(doc[3])
        self._refInfo.set(doc[5])

        # location
        if doc[6]!=None:
            recordsLocation = dbAnnot.db.execute("SELECT * from locations where ID="+str(doc[6]))
            location = recordsLocation.fetchone()
            self._locationInfo.set(location[2])
        else:
            self._locationInfo.set("-")
        # person    
        if doc[7]!=None:
            recordsPerson = dbAnnot.db.execute("SELECT * from persons where ID="+str(doc[7]))
            person = recordsPerson.fetchone()
            self._authorInfo.set(person[1])
        else:
            self._authorInfo.set("-")

        self.updateAnnotations()

    def mouseUp(self, event):
        self.clearAnnotation()
        ranges = self.getSelectedWords()
        if ranges == None:
            self._annotate.config(state=tk.DISABLED)
            return
        self._annotate.config(state=tk.NORMAL)
        self._citedText.insert(tk.INSERT, self._text.get(*ranges))

    def clearAnnotation(self):
        self._citedText.delete("1.0", tk.END)
        self._annotate.config(state=tk.DISABLED)

    def getSelectedWords(self):       
        ranges = self._text.tag_ranges(tk.SEL)
        if ranges==None or len(ranges)==0:
            return None

        range0Str = str(ranges[0]) + " wordstart"
        range1Str = str(ranges[1]) + " wordend"

        # if double click then it also select 1 last char that needs to be removed
        firstChar = self._text.get(range0Str, range0Str + "+ 1 chars")
        lastChar = self._text.get(range1Str + "- 1 chars", range1Str)
        if not firstChar.isalnum():
            range0Str = str(ranges[0]) + " wordstart +1 chars"
        if not lastChar.isalnum():
            range1Str = str(ranges[1]) + " wordend -1 chars"
               
        range0 = self._text.index(range0Str)
        range1 = self._text.index(range1Str)
        adjustedRanges = (range0, range1)
        return adjustedRanges

    def addAnnotation(self):
        self._rangeSelected = self.getSelectedWords()
        selectedText = self._text.get(*self._rangeSelected)
        if self._typeSelected=="person":
            self._annotPerson = PersonAnnotation(self._window, selectedText)
            self._annotPerson .signalAdd = self.addPerson
            return
        if self._typeSelected=="location":
            self._annotLocation = LocationAnnotation(self._window, selectedText)
            self._annotLocation.signalAdd = self.addLocation
            return
        if self._typeSelected=="keyword":
            self._annotKeyword = KeywordAnnotation(self._window, selectedText)
            self._annotKeyword.signalAdd = self.addKeyword
            return


    def resetTags(self):       
        self._annotations = []

        for tag in self._text.tag_names():
            if tag.startswith("overlap_"):
                self._text.tag_delete(tag)

        # clear tags before adding them
        self._text.tag_delete("keyword")
        self._text.tag_delete("location")
        self._text.tag_delete("person")

        self._text.tag_config("keyword", background="#A8DDB5", foreground="black", font=("arial", self.fontSize, "bold"))
        self._text.tag_config("location", background="#FFE28A", foreground="black", font=("arial", self.fontSize, "bold"))
        self._text.tag_config("person", background="#F17A7A", foreground="black", font=("arial", self.fontSize, "bold"))

         # Overlap colors
        self._text.tag_config("overlap_location_person", background="#F8AE82")
        self._text.tag_config("overlap_keyword_location", background="#D4E09F")
        self._text.tag_config("overlap_keyword_person", background="#CCACA8")

    
    def updateAnnotations(self):
        self.resetTags()

        index = self._docsList.curselection()[0]
        docId = self._docs[self._docsList.get(index)]
        records = dbAnnot.db.execute("SELECT * from annotations where id_doc="+str(docId))

        intervals = []

        for row in records:
            typeAnnotation = row[1]
            begin = row[2]
            end = row[3]
            self._text.tag_add(typeAnnotation, begin, end)
            self._annotations.append(row)

            # Store each annotation to compare it with the others.
            intervals.append((typeAnnotation, begin, end))

        # Compare every pair of annotations.
        for i in range(len(intervals)):
            for j in range(i + 1, len(intervals)):

                type1, begin1, end1 = intervals[i]
                type2, begin2, end2 = intervals[j]

                # Ignore pairs belonging to the same annotation type.
                if type1 == type2:
                    continue

                # Determine which overlap color should be used.
                types = sorted([type1, type2])
                overlapTag = "overlap_" + types[0] + "_" + types[1]

                # Find where the shared text region begins.
                if self._text.compare(begin1, ">", begin2):
                    overlapBegin = begin1
                else:
                    overlapBegin = begin2

                # Find where the shared text region ends.
                if self._text.compare(end1, "<", end2):
                    overlapEnd = end1
                else:
                    overlapEnd = end2

                # An overlap exists only if its start is before its end.
                if self._text.compare(overlapBegin, "<", overlapEnd):
                    self._text.tag_add(overlapTag, overlapBegin, overlapEnd)
                    self._text.tag_raise(overlapTag)
   
        # Keep the text selection visible above annotation colors.
        self._text.tag_raise("sel")
    
    def createDocsTab(self):
        self._docsTab = ttk.Frame(self._tabs)
        self._docsTab.pack(fill=tk.BOTH, expand=True)

        self._tabs.add(self._docsTab, text="annotate")

        self._worksList = tk.Listbox(self._docsTab, exportselection=False, selectmode=tk.SINGLE, width = 20,font=("arial", 12)) 
        self._worksList.bind('<<ListboxSelect>>',self.selectWork)
        self._worksList.pack(side = tk.LEFT, fill = tk.Y)

        self.updateWorkList()
     
        self._docsList = tk.Listbox(self._docsTab, exportselection=False, selectmode=tk.SINGLE, width = 20,font=("arial", 12))
        self._docsList.pack(side = tk.LEFT, fill = tk.Y)

        self._docsList.bind('<<ListboxSelect>>',self.selectDoc)

        # set scroll bar to list box for when entries exceed size of list box
        self._docsScroll = tk.Scrollbar(self._docsTab, orient = tk.VERTICAL)
        self._docsScroll.config(command = self._docsList.yview)
        self._docsScroll.pack(side = tk.LEFT, fill = tk.Y)
        self._docsList.config(yscroll= self._docsScroll.set)     
        
    def selectType(self, text, v):
        self._typeSelected = text

    def changeFontSize(self, amount):
        self.fontSize = max(8, min(30, self.fontSize + amount))
        self._text.config(font=("arial", self.fontSize))

        # Update the font size of annotations
        for tag in ["keyword", "location", "person"]:
            self._text.tag_config(tag, font=("arial", self.fontSize, "bold"))


    def getKeywordTooltip(self, idAnnotation):
        # get idKeyword linked to this idAnnotation
        records = dbAnnot.db.execute("SELECT id_keyword from annotationKeyword where id_annotation="+str(idAnnotation))
        idKeyword = records.fetchone()[0]

        # get person info
        records = dbAnnot.db.execute("SELECT * from keywords where id="+str(idKeyword))
        keyword = records.fetchone()

        # build text
        return "keyword: "+keyword[1]+"\n\ninfo: "+keyword[2]

    def getPersonTooltip(self, idAnnotation):
        # get idPerson linked to this idAnnotation
        records = dbAnnot.db.execute("SELECT id_person from annotationPerson where id_annotation="+str(idAnnotation))
        idPerson = records.fetchone()[0]

        # get person info
        records = dbAnnot.db.execute("SELECT * from persons where id="+str(idPerson))
        person = records.fetchone()

        #print("id annotation:",idAnnotation,"id person:",idPerson,"name:",person[1])
        # build text
        return "person: "+person[1]+"\n\ninfo: "+person[2]

    def getLocationTooltip(self, idAnnotation):
        # get idLocation linked to this idAnnotation
        records = dbAnnot.db.execute("SELECT id_location from annotationLocation where id_annotation="+str(idAnnotation))
        idLocation = records.fetchone()[0]

        # get person info
        records = dbAnnot.db.execute("SELECT * from locations where id="+str(idLocation))
        location = records.fetchone()

        #print("id annotation:",idAnnotation,"id person:",idPerson,"name:",person[1])
        # build text
        text = "location: "+location[2]+"\n\ninfo:"
        if location[1]==None:
            text += "(custom location)"
        # from geonames
        else:
            featureClass = location[6]
            featureCode = location[7]
            country = location[8]
            pos = str(location[4])+"/"+str(location[5])

            text+= " ("+country+")"
            if featureClass=="P":
                text += ", settlement"
            elif featureClass=="A":
                text += ", region"  
            # no SPOTS to avoid businesses               
            elif featureClass!="S":                
                text += ", class:"+featureClass+", code:"+featureCode
                
            text += " ["+pos+"]"        
        return text

    def setTooltipText(self):
        currentIndex = self._text.index(tk.CURRENT)
        for annotation in self._annotations:
            if self._text.compare(currentIndex, ">=", annotation[2]) and self._text.compare(currentIndex, "<=", annotation[3]):
                if annotation[1]=="person":
                    return self.getPersonTooltip(annotation[0])
                elif annotation[1]=="location":
                    return self.getLocationTooltip(annotation[0])
                elif annotation[1]=="keyword":
                    return self.getKeywordTooltip(annotation[0])

        return "" 

    def updateTooltip(self, tooltipText):
        tooltipText.msg = self.setTooltipText()
        self._window.after(100, self.updateTooltip, tooltipText)
        """
        TODO hide tooltipText if msg is empty
        if tooltipText.msg=="" and tooltipText.state()!='withdrawn':
            print("aa")
            tooltipText.withdraw()
        elif tooltipText.msg!="" and tooltipText.state()!='normal':
            print("bb")
            tooltipText.deiconify()
        """

    def createCiteFrame(self):

        citeFrame = tk.Frame(self._docsTab)
        citeFrame.pack(fill=tk.BOTH, expand=True)

        frame = tk.Frame(citeFrame)
        frame.pack(fill=tk.X, pady=1)

        label = tk.Label(frame, text="Title: ", width=10)
        label.pack(side=tk.LEFT, padx=1)
        self._titleInfo = tk.StringVar()
        self._titleInfo.set("-")
        entry = tk.Entry(frame, textvariable=self._titleInfo)
        entry.pack(side=tk.LEFT, fill=tk.X, padx=1, expand=True)
        entry.config(state="readonly")
    
        frame = tk.Frame(citeFrame)
        frame.pack(fill=tk.X)
       
        label = tk.Label(frame, text="Reference: ", width=10)
        label.pack(side=tk.LEFT, padx=1, pady=1)
        self._refInfo = tk.StringVar()
        self._refInfo.set("-")
        entry = tk.Entry(frame, textvariable=self._refInfo)
        entry.pack(side=tk.LEFT, fill=tk.X, padx=1, expand=True)
        entry.config(state="readonly")

        label = tk.Label(frame, text="Date: ", width=10)
        label.pack(side=tk.LEFT, padx=1, pady=5)
        self._dateInfo = tk.StringVar()
        self._dateInfo.set("-")
        entry = tk.Entry(frame, textvariable=self._dateInfo)
        entry.pack(side=tk.LEFT, fill=tk.X, padx=1, expand=True)
        entry.config(state="readonly")

        label = tk.Label(frame, text="Author: ", width=10)
        label.pack(side=tk.LEFT, padx=1, pady=5)
        self._authorInfo = tk.StringVar()
        self._authorInfo.set("-")
        entry = tk.Entry(frame, textvariable=self._authorInfo)
        entry.pack(side=tk.LEFT, fill=tk.X, padx=1, expand=True)
        entry.config(state="readonly")

        label = tk.Label(frame, text="Location: ", width=10)
        label.pack(side=tk.LEFT, padx=1, pady=5)
        self._locationInfo = tk.StringVar()
        self._locationInfo.set("-")
        entry = tk.Entry(frame, textvariable=self._locationInfo)
        entry.pack(side=tk.LEFT, fill=tk.X, padx=1, expand=True)
        entry.config(state="readonly")

        textFrame = tk.Frame(citeFrame)
        textFrame.pack(fill=tk.BOTH, expand=True)
        textFrame.pack_propagate(False)

        # Font size controls
        zoomFrame = tk.Frame(textFrame)
        zoomFrame.pack(fill=tk.X)

        plusButton = tk.Button(zoomFrame, text="+", command=lambda: self.changeFontSize(1))
        plusButton.pack(side=tk.RIGHT, padx=5)

        minusButton = tk.Button(zoomFrame, text="-", command=lambda: self.changeFontSize(-1))
        minusButton.pack(side=tk.RIGHT)

        self.fontSize = 12
        self._text = tk.Text(textFrame, font=("arial", self.fontSize))
        self._text.pack(fill=tk.BOTH, expand=True)
        self._text.bind("<ButtonRelease-1>", self.mouseUp)
        self._text.config(wrap=tk.WORD)
        self._text.config(state=tk.DISABLED)
        tooltipText = ToolTip(self._text)
        tooltipText.follow = True 
        tooltipText.delay = 0.1
        #self.rt = RepeatedTimer(0.1, self.updateTooltip, tooltipText)
        self._window.after(100, self.updateTooltip, tooltipText)

        self.resetTags()
        citedTextFrame = tk.Frame(citeFrame)
        citedTextFrame.pack(fill=tk.X, pady=5)

        self._citedText = tk.Text(citedTextFrame, font=("arial","12","italic"), height=10)
        self._citedText.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # options for the new annotation
        options = tk.Frame(citeFrame, relief=tk.RAISED, borderwidth=1)
        options.pack(side=tk.RIGHT, fill=tk.Y)
    
        # type of annotation
        annotTypes = [("keyword", 2, "#A8DDB5"),("location", 1, "#FFE28A"),("person", 3, "#F17A7A")]

        varType = tk.IntVar()
        # first selection before any click
        varType.set(annotTypes[0][1])
        self._typeSelected = annotTypes[0][0]

        for name, idName,color in annotTypes:
            tk.Radiobutton(options, text=name, bg=color, fg="black", activeforeground="black", variable=varType, value=idName, command=lambda t=name, v=varType: self.selectType(t, v)).pack(side=tk.LEFT)
            
        # ok button
        self._annotate = tk.Button(options, text ="annotate",command=self.addAnnotation)
        self._annotate.pack(side=tk.RIGHT, padx=5, pady=5)
        self._annotate.config(state=tk.DISABLED)

    def newWork(self):
        addWork = NewWork(self._window)
        addWork.signalAdded = self.workAdded

    def updateWorkEntries(self):
        records = dbAnnot.db.execute("SELECT * from works")
        self._seriesIds = {}
        self._seriesCombo['values'] = []

        seriesList = []
        for row in records:
            self._seriesIds[row[3]] = row[0]
            seriesList.append(row[3])

        self._seriesCombo['values'] = seriesList

    def workAdded(self, newId, newTitle):
        self.updateWorkEntries()
        self._seriesCombo.set(newTitle)

    def createAddSourceFrame(self):
        self._worksTab = ttk.Frame(self._tabs)
        self._tabs.add(self._worksTab, text="add source")

        frame = tk.Frame(self._worksTab)
        frame.pack(fill=tk.X)

        label = tk.Label(frame, text="Title", width=10)
        label.pack(side=tk.LEFT, padx=5, pady=5)

        self._docTitle = tk.StringVar()
        entry  = tk.Entry(frame, textvariable=self._docTitle, width=20)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)   
   
        frame = tk.Frame(self._worksTab)
        frame.pack(fill=tk.X)
    
        # work
        label = tk.Label(frame, text="Series", width=20)
        label.pack(side=tk.LEFT, padx=5, pady=5)

        self._seriesCombo = ttk.Combobox(frame)
        self.updateWorkEntries()
        self._seriesCombo.pack(side=tk.LEFT, padx=5)   
        self._seriesCombo.config(state="readonly")
   
        addButton = tk.Button(frame, text ="new", command=self.newWork)
        addButton.pack(side=tk.LEFT, padx=1, pady=5)

        label = tk.Label(frame, text="Reference", width=12)
        label.pack(side=tk.LEFT, padx=5, pady=5)

        self._refDoc = tk.StringVar()
        entry  = tk.Entry(frame, textvariable=self._refDoc, width=20)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)   
       
        frame = tk.Frame(self._worksTab)
        frame.pack(fill=tk.X)
    
        label = tk.Label(frame, text="Date (DD/MM/YYYY)", width=20)
        label.pack(side=tk.LEFT, padx=5, pady=5)

        self._date = tk.StringVar()
        entry  = tk.Entry(frame, textvariable=self._date, width=20)
        entry.pack(side=tk.LEFT, padx=5, pady=5)

        label = tk.Label(frame, text="Author", width=20)
        label.pack(side=tk.LEFT, padx=5, pady=5)

        self._author = tk.StringVar()
        self._author.set("")
        entry  = tk.Entry(frame, textvariable=self._author, width=20)
        entry.pack(side=tk.LEFT, padx=5, pady=5)
        entry.config(state="readonly")
  
        addButton = tk.Button(frame, text ="add", command=self.addAuthorToDoc)
        addButton.pack(side=tk.LEFT, padx=1, pady=5)
         
        label = tk.Label(frame, text="Location", width=10)
        label.pack(side=tk.LEFT, padx=5, pady=5)
    
        self._location = tk.StringVar()
        self._location.set("")
        entry  = tk.Entry(frame, textvariable=self._location, width=20)
        entry.pack(side=tk.LEFT, padx=5, pady=5)   
        entry.config(state="readonly")
    
        addButton = tk.Button(frame, text ="add", command=self.addLocationToDoc)
        addButton.pack(side=tk.LEFT, padx=1, pady=5)
      
        frame = tk.Frame(self._worksTab)
        frame.pack(fill=tk.BOTH, expand=True)
    
        self._docText = tk.Text(frame, font=("arial","12"))
        self._docText.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self._docText.config(wrap=tk.WORD)
        
        frame = tk.Frame(self._worksTab)
        frame.pack(fill=tk.X)

        addButton = tk.Button(frame, text ="create", command=self.addDoc)
        addButton.pack(side=tk.RIGHT, padx=20, pady=5)

    def addDoc(self):
        idWork = self._seriesIds[self._seriesCombo.get()]
        sql = 'INSERT INTO docs (id_work, title, date, text, ref'
        valuesSql = " VALUES (?,?,?,?,?"
        values = (idWork, self._docTitle.get(), self._date.get(), self._docText.get(1.0, tk.END), self._refDoc.get())

        if self._location.get()!="":
            sql += ",id_location"
            valuesSql += ",?"
            values += (self._locationId,)
        
        if self._author.get()!="":
            sql += ",id_author"
            valuesSql += ",?"    
            values += (self._authorId,)

        sql += ") "            
        valuesSql += ")"            
        sql += valuesSql
        #print("query: ",sql)
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        tk.messagebox.showinfo("Sucess", "new doc created")
        self.updateWorkList()

    def updateWorkList(self):

        self._works = {}
        listValues = []

        self._worksList.delete(0, tk.END)

        records = dbAnnot.db.execute("SELECT * FROM works")

        for row in records:
            listValues.append(row[3])
            self._works[row[3]] = row[0]


        listValues = sorted(listValues, key=str.casefold)
        index = 0

        for value in listValues:
            self._worksList.insert(index, value)
            index += 1
        

    def setAuthor(self, idPerson):
    
        records = dbAnnot.db.execute("SELECT * from persons where id="+str(idPerson))
        person = records.fetchone()

        self._author.set(person[1])
        self._authorId = idPerson

    def addAuthorToDoc(self):   
        author = PersonAnnotation(self._window, "")
        author.signalAdd = self.setAuthor


    def setLocation(self, idLocation):
        records = dbAnnot.db.execute("SELECT * from locations where id="+str(idLocation))
        location = records.fetchone()

        self._location.set(location[2])
        self._locationId = idLocation 

    def addLocationToDoc(self):
        location = LocationAnnotation(self._window, "type to find locations")
        location.signalAdd = self.setLocation

    def addKeyword(self, idKeyword):
        # insert annotation
        sql = 'INSERT INTO annotations (type,begin,end,id_doc) VALUES (?,?,?,?)'
      
        index = self._docsList.curselection()[0]
        docId = self._docs[self._docsList.get(index)]

        values = (self._typeSelected, str(self._rangeSelected[0]), str(self._rangeSelected[1]), str(docId))
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()
        
        # get annotation id 
        records = dbAnnot.db.execute("SELECT last_insert_rowid()")
        idAnnot = records.fetchone()[0]
        
        # insert person-annotation ids
        sql = 'INSERT INTO annotationKeyword (id_annotation,id_keyword) VALUES (?,?)'
        values = (idAnnot, idKeyword)
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        self.updateAnnotations()

    def addPerson(self, idPerson):
        # insert annotation
        sql = 'INSERT INTO annotations (type,begin,end,id_doc) VALUES (?,?,?,?)'
        
        index = self._docsList.curselection()[0]
        docId = self._docs[self._docsList.get(index)]

        values = (self._typeSelected, str(self._rangeSelected[0]), str(self._rangeSelected[1]), str(docId))
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()
        
        # get annotation id 
        records = dbAnnot.db.execute("SELECT last_insert_rowid()")
        idAnnot = records.fetchone()[0]
        
        # insert person-annotation ids
        sql = 'INSERT INTO annotationPerson (id_annotation,id_person) VALUES (?,?)'
        values = (idAnnot, idPerson)
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        self.updateAnnotations()

    def addLocation(self, idLocation):
        # insert annotation
        sql = 'INSERT INTO annotations (type,begin,end,id_doc) VALUES (?,?,?,?)'
  
        index = self._docsList.curselection()[0]
        docId = self._docs[self._docsList.get(index)]

        values = (self._typeSelected, str(self._rangeSelected[0]), str(self._rangeSelected[1]), str(docId))
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()
        
        # get annotation id 
        records = dbAnnot.db.execute("SELECT last_insert_rowid()")
        idAnnot = records.fetchone()[0]
        
        # insert location-annotation ids
        sql = 'INSERT INTO annotationLocation (id_annotation,id_location) VALUES (?,?)'
        values = (idAnnot, idLocation)
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        self.updateAnnotations()

    def onClose(self):
        #self.rt.stop()
        self._window.destroy()

    def run(self):
        self._window.protocol("WM_DELETE_WINDOW", self.onClose)
        self._window.mainloop()


def main():

    dbAnnot.init()

    ui = UI()
    ui.run();

if __name__ == "__main__":
    main()

