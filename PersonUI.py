#!/usr/bin/python3

import tkinter as tk
import sqlite3 as sq 

from tkinter import ttk

import dbAnnot
from dbAnnot import *

class PersonAnnotation(tk.Toplevel):

    # signal to main window that it needs to update citations
    signalAdd = None
    # Signal to open a source document
    signalOpen = None
    _ids = {}

    def __init__(self, parent, quote):
        super().__init__(parent)
        self.geometry("850x750+300+150")
        self.title("select person")

        # Main container for the two panels
        mainFrame = tk.Frame(self)
        mainFrame.pack(fill=tk.BOTH, expand=True)

        # Left panel: search and person list
        leftFrame = tk.Frame(mainFrame)
        leftFrame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right panel: person details and editing
        rightFrame = tk.Frame(mainFrame)
        rightFrame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        frame1 = tk.Frame(leftFrame, padx=5, pady=5, relief=tk.RAISED, borderwidth=1)
        frame1.pack(fill=tk.X)
        lbl1 = tk.Label(frame1, text="Search", width=6)
        lbl1.pack(side=tk.LEFT, padx=5, pady=5)
    
        self._search= tk.StringVar()
        self._search.trace_add("write", self.filterList)
        self._searchEntry = tk.Entry(frame1, textvariable=self._search)
        self._searchEntry.pack(fill=tk.X, padx=5, side=tk.LEFT, expand=True)
        self._addButton = tk.Button(frame1, text="add new", command=self.addNew)
        self._addButton.pack(side=tk.RIGHT, padx=5, pady=5)
 
        frame2 = tk.Frame(leftFrame, padx=5, pady=5, borderwidth=1, relief=tk.RAISED)
        frame2.pack(fill=tk.BOTH, expand=True)
        lbl2 = tk.Label(frame2, text="Entries", width=6)
        lbl2.pack(side=tk.LEFT, anchor=tk.N, padx=5, pady=5)
        self._entries = tk.Listbox(frame2, exportselection=False, selectmode=tk.SINGLE, width = 20, font=("arial", 12))
        self._entries.pack(fill = tk.BOTH, expand=True)
        self._entries.bind('<<ListboxSelect>>',self.select)

        # Person details panel
        detailsFrame = tk.Frame(rightFrame, padx=10, pady=10)
        detailsFrame.pack(fill=tk.BOTH, expand=True)

        # Person name
        nameLabel = tk.Label(detailsFrame, text="Name")
        nameLabel.pack(anchor=tk.W)

        self._personName = tk.StringVar()
        self._nameEntry = tk.Entry(detailsFrame, textvariable=self._personName)
        self._nameEntry.pack(fill=tk.X, pady=5)
        self._nameEntry.config(state=tk.DISABLED)

        # Names and references found in the corpus
        referencesLabel = tk.Label(detailsFrame, text="Names & references")
        referencesLabel.pack(anchor=tk.W)

        self._referencesList = tk.Listbox(detailsFrame, height=5)
        self._referencesList.pack(fill=tk.X, pady=5)

        # Show occurrences when a reference is selected
        self._referencesList.bind(
            '<<ListboxSelect>>',
            self.selectReference
        )

        # Original document context
        contextLabel = tk.Label(detailsFrame, text="Original context")
        contextLabel.pack(anchor=tk.W)

        # List of occurrences for the selected reference
        self._occurrencesList = tk.Listbox(detailsFrame, height=3)
        self._occurrencesList.pack(fill=tk.X, pady=5)

        # Show context when an occurrence is selected
        self._occurrencesList.bind(
            '<<ListboxSelect>>',
            self.selectOccurrence
        )

        # Text surrounding the original annotation
        self._contextText = tk.Text(detailsFrame, height=5, wrap=tk.WORD)
        self._contextText.pack(fill=tk.X, pady=5)
        self._contextText.config(state=tk.DISABLED)

        # Button to open the full document
        self._openButton = tk.Button(
            detailsFrame,
            text="Open document",
            command=self.openDocument)
        self._openButton.pack(anchor=tk.E, pady=5)
        self._openButton.config(state=tk.DISABLED)

        # Person information
        infoLabel = tk.Label(detailsFrame, text="Info")
        infoLabel.pack(anchor=tk.W)

        self._personInfo = tk.Text(detailsFrame, height=10, wrap=tk.WORD)
        self._personInfo.pack(fill=tk.BOTH, expand=True, pady=5)
        self._personInfo.config(state=tk.DISABLED)

        # Edit button
        self._editButton = tk.Button(detailsFrame, text="Edit", command=self.editPerson)
        self._editButton.pack(anchor=tk.E, pady=5)
        self._editButton.config(state=tk.DISABLED)

        # Save person changes
        self._saveButton = tk.Button(detailsFrame, text="Save", command=self.savePerson)
        self._saveButton.pack(anchor=tk.E, pady=5)
        self._saveButton.config(state=tk.DISABLED)

        # Cancel editing without saving changes
        self._cancelEditButton = tk.Button(
            detailsFrame,
            text="Cancel editing",
            command=self.cancelEdit)
        self._cancelEditButton.pack(anchor=tk.E, pady=5)
        self._cancelEditButton.config(state=tk.DISABLED)

        self._editing = False
        self._newPerson = False
        self._selectedPersonId = None
       
        frame3 = tk.Frame(self, padx=5, pady=5, relief=tk.RAISED, borderwidth=1)
        frame3.pack(fill=tk.X)
        cancelButton = tk.Button(frame3, text ="cancel",command=self.cancel)
        cancelButton.pack(side=tk.RIGHT)

        # change for okButton
        self._ok = tk.Button(frame3, text ="ok",command=self.ok)
        self._ok.pack(side=tk.RIGHT)
        self._ok.config(state=tk.DISABLED)

        self._search.set(quote)

    def cancelEdit(self):

        # Stop editing
        self._editing = False
        self._newPerson = False

        # Lock the fields
        self._nameEntry.config(state=tk.DISABLED)
        self._personInfo.config(state=tk.DISABLED)

        # Update buttons
        self._saveButton.config(state=tk.DISABLED)
        self._cancelEditButton.config(state=tk.DISABLED)

        # Restore the selected person's information
        if self._selectedPersonId is not None:

            records = dbAnnot.db.execute(
                "SELECT * FROM persons WHERE id=?",
                (self._selectedPersonId,)
            )
            person = records.fetchone()

            if person is not None:
                self._personName.set(person[1])

                self._personInfo.config(state=tk.NORMAL)
                self._personInfo.delete("1.0", tk.END)

                if person[2] is not None:
                    self._personInfo.insert("1.0", person[2])

                self._personInfo.config(state=tk.DISABLED)

                self._editButton.config(state=tk.NORMAL)
                self._ok.config(state=tk.NORMAL)

        else:
            # Clear fields if a new person was being created
            self._personName.set("")

            # Clear the previous person selection
            self._entries.selection_clear(0, tk.END)

            self._personInfo.config(state=tk.NORMAL)
            self._personInfo.delete("1.0", tk.END)
            self._personInfo.config(state=tk.DISABLED)

            self._editButton.config(state=tk.DISABLED)
            self._ok.config(state=tk.DISABLED)

        # Enable the person list again
        self._entries.config(state=tk.NORMAL)

        # Enable search again
        self._searchEntry.config(state=tk.NORMAL)

        # Enable Add New again
        self._addButton.config(state=tk.NORMAL)

    def editPerson(self):
        self._editing = True
        self._newPerson = False

        # Enable editing
        self._personInfo.config(state=tk.NORMAL)
        self._saveButton.config(state=tk.NORMAL)

        # Enable cancelling the current edit
        self._cancelEditButton.config(state=tk.NORMAL)
        self._editButton.config(state=tk.DISABLED)

        # Disable search while editing
        self._searchEntry.config(state=tk.DISABLED)

        # Prevent changing person while editing
        self._entries.config(state=tk.DISABLED)
        self._ok.config(state=tk.DISABLED)

        # Disable Add New while creating a person
        self._addButton.config(state=tk.DISABLED)

        # Disable Add New while editing
        self._addButton.config(state=tk.DISABLED)

    def addNew(self):
        self._editing = True
        self._newPerson = True
        self._selectedPersonId = None

        # Enable the fields
        self._nameEntry.config(state=tk.NORMAL)
        self._personInfo.config(state=tk.NORMAL)

        # Prepare empty fields for a new person
        self._personName.set(self._search.get())
        self._personInfo.delete("1.0", tk.END)

        self._saveButton.config(state=tk.NORMAL)

        # Enable cancelling the current edit
        self._cancelEditButton.config(state=tk.NORMAL)
        self._editButton.config(state=tk.DISABLED)
        self._ok.config(state=tk.DISABLED)

        # Disable search while creating a person
        self._searchEntry.config(state=tk.DISABLED)

        # Prevent selecting another person
        self._entries.config(state=tk.DISABLED)
        self._entries.selection_clear(0, tk.END)

    def savePerson(self):
        name = self._personName.get().strip()
        info = self._personInfo.get("1.0", tk.END).strip()

        if name == "":
            return

        if self._newPerson:
            # Insert a new person
            sql = "INSERT INTO persons (name, info) VALUES (?, ?)"

            values = (name, info)
            dbAnnot.db.execute(sql, values)

            self._selectedPersonId = dbAnnot.db.lastrowid

        else:
            # Update only the person's information
            sql = "UPDATE persons SET info=? WHERE id=?"

            values = (info, self._selectedPersonId)
            dbAnnot.db.execute(sql, values)

        # Enable the person list again
        self._entries.config(state=tk.NORMAL)

        dbAnnot.conn.commit()

        self._editing = False
        self._newPerson = False

        # Lock the fields again
        self._nameEntry.config(state=tk.DISABLED)
        self._personInfo.config(state=tk.DISABLED)

        # Enable search again
        self._searchEntry.config(state=tk.NORMAL)

        # Enable Add New again
        self._addButton.config(state=tk.NORMAL)

        # Update buttons after saving
        self._saveButton.config(state=tk.DISABLED)
        self._cancelEditButton.config(state=tk.DISABLED)
        self._editButton.config(state=tk.NORMAL)

        # Refresh the person list
        self._search.set("")
        self.updateEntries("")

        # Find and select the saved person
        for i in range(self._entries.size()):
            personName = self._entries.get(i)
            personId = self._ids[personName]

            if personId == self._selectedPersonId:
                self._entries.selection_set(i)
                self._entries.activate(i)
                self._entries.see(i)
                break

        self._ok.config(state=tk.NORMAL)

    def added(self):
        self._search.set("")

    # XRC TODO fer-ho com amb places basat en select, és molt més ràpidF
    def updateEntries(self, txt):
        records = dbAnnot.db.execute("SELECT * from persons")

        self._entries.delete(0, tk.END)
        # dictionary with name as key and id as value
        self._ids = {}
        listValues = []

        for row in records:
            personName = row[1]
            # filter if search is being used
            if txt!="" and personName.lower().find(txt.lower())==-1:
                continue
                
            self._ids[personName] = row[0]
            listValues.append(personName)

        listValues = sorted(listValues, key=str.casefold)
        index = 0

        for value in listValues:
            self._entries.insert(index, value)
            index += 1

    def select(self, event):

        # Do not change person while editing
        if self._editing:
            return

        # Check if a person is selected
        if len(self._entries.curselection()) == 0:
            return

        # Get the selected person
        index = self._entries.curselection()[0]
        personName = self._entries.get(index)
        idPerson = self._ids[personName]

        # Remember the selected person
        self._selectedPersonId = idPerson

        # Get person data from the database
        sql = "SELECT * FROM persons WHERE id=?"
        values = (idPerson,)

        records = dbAnnot.db.execute(sql, values)
        person = records.fetchone()

        if person is None:
            return

        # Display person name
        self._personName.set(person[1])

        # Display person information
        self._personInfo.config(state=tk.NORMAL)
        self._personInfo.delete("1.0", tk.END)

        if person[2] is not None:
            self._personInfo.insert("1.0", person[2])

        self._personInfo.config(state=tk.DISABLED)

        # Lock the name field
        self._nameEntry.config(state=tk.DISABLED)

        # Return to view mode
        self._editing = False
        self._newPerson = False

        # Update buttons
        self._editButton.config(state=tk.NORMAL)
        self._saveButton.config(state=tk.DISABLED)
        self._cancelEditButton.config(state=tk.DISABLED)
        self._ok.config(state=tk.NORMAL)

        # Show names and references linked to this person
        self.updateReferences(idPerson)

    def updateReferences(self, idPerson):

        # Clear previous references and occurrences
        self._referencesList.delete(0, tk.END)
        self._occurrencesList.delete(0, tk.END)

        # Clear previous context
        self._contextText.config(state=tk.NORMAL)
        self._contextText.delete("1.0", tk.END)
        self._contextText.config(state=tk.DISABLED)

        self._openButton.config(state=tk.DISABLED)

        # Find all annotations linked to this person
        sql = """
            SELECT annotations.begin, annotations.end,
                   docs.text, docs.id
            FROM annotationPerson
            JOIN annotations
                ON annotationPerson.id_annotation = annotations.id
            JOIN docs
                ON annotations.id_doc = docs.id
            WHERE annotationPerson.id_person = ?
        """

        values = (idPerson,)
        records = dbAnnot.db.execute(sql, values)

        # Store all occurrences for each reference
        self._references = {}

        for row in records:

            begin = row[0]
            end = row[1]
            docText = row[2]
            docId = row[3]

            # Get line and character positions
            beginLine, beginChar = begin.split(".")
            endLine, endChar = end.split(".")

            # Get the annotated line
            lines = docText.split("\n")
            line = lines[int(beginLine) - 1]

            # Extract the annotated text
            reference = line[int(beginChar):int(endChar)]
            reference = reference.strip()

            if reference == "":
                continue

            # Create a list for each new reference
            if reference not in self._references:
                self._references[reference] = []

            # Save this occurrence
            occurrence = (docId, begin, end, docText)
            self._references[reference].append(occurrence)

        # Display references and their counts
        self._referenceNames = []

        for reference in self._references:

            count = len(self._references[reference])
            displayText = reference + " (" + str(count) + ")"

            self._referencesList.insert(tk.END, displayText)
            self._referenceNames.append(reference)

    def selectReference(self, event):

        # Check if a reference is selected
        if len(self._referencesList.curselection()) == 0:
            return

        # Get the selected reference
        index = self._referencesList.curselection()[0]
        reference = self._referenceNames[index]

        # Get all occurrences of this reference
        self._selectedOccurrences = self._references[reference]

        # Clear the previous occurrences
        self._occurrencesList.delete(0, tk.END)

        # Clear the previous context
        self._contextText.config(state=tk.NORMAL)
        self._contextText.delete("1.0", tk.END)
        self._contextText.config(state=tk.DISABLED)

        self._openButton.config(state=tk.DISABLED)

        # Display each occurrence
        for i in range(len(self._selectedOccurrences)):

            occurrence = self._selectedOccurrences[i]
            docId = occurrence[0]

            text = "Occurrence " + str(i + 1)
            text = text + " - Document " + str(docId)

            self._occurrencesList.insert(tk.END, text)

    def selectOccurrence(self, event):

        # Check if an occurrence is selected
        if len(self._occurrencesList.curselection()) == 0:
            return

        index = self._occurrencesList.curselection()[0]

        # Get the selected occurrence
        occurrence = self._selectedOccurrences[index]

        docId = occurrence[0]
        begin = occurrence[1]
        end = occurrence[2]
        docText = occurrence[3]

        # Get the annotated line
        beginLine, beginChar = begin.split(".")
        endLine, endChar = end.split(".")

        lines = docText.split("\n")
        line = lines[int(beginLine) - 1]

        # Extract some text before and after the annotation
        start = max(0, int(beginChar) - 100)
        finish = min(len(line), int(endChar) + 100)

        context = line[start:finish]

        # Display the original context
        self._contextText.config(state=tk.NORMAL)
        self._contextText.delete("1.0", tk.END)
        self._contextText.insert("1.0", context)
        self._contextText.config(state=tk.DISABLED)

        # Remember the document to open later
        self._selectedDocumentId = docId
        self._selectedBegin = begin
        self._selectedEnd = end

        # Enable Open document
        self._openButton.config(state=tk.NORMAL)

    def openDocument(self):

        # Send the selected document and annotation position
        docId = self._selectedDocumentId
        begin = self._selectedBegin
        end = self._selectedEnd

        self.signalOpen(docId, begin, end)

        # Close the person window
        self.destroy()

    def cancel(self):
        self.destroy();

    def filterList(self, var, index, mode):
        self.updateEntries(self._search.get())
    
    def ok(self):

        # Do not confirm while editing
        if self._editing:
            return

        # Check that a person is selected
        if self._selectedPersonId is None:
            return

        # Send the selected person ID to the main window
        self.signalAdd(self._selectedPersonId)

        # Close the window
        self.destroy()

class PersonInsertion(tk.Toplevel):   

    # signal/callback to update person entries
    signalAdded = None
    
    def __init__(self, parent, initialText):
        super().__init__(parent)
        self.geometry("400x300+800+300")
        self.title("add new person")

        frame1 = tk.Frame(self)
        frame1.pack(fill=tk.X)

        lbl1 = tk.Label(frame1, text="Name", width=6)
        lbl1.pack(side=tk.LEFT, padx=5, pady=5)
        
        self._personName = tk.StringVar()
        self._personName.set(initialText)
        self._personName.trace_add("write", self.enableEntry)
        
        entry1 = tk.Entry(frame1, textvariable=self._personName)
        entry1.pack(fill=tk.X, padx=5, expand=True)

        frame2 = tk.Frame(self)
        frame2.pack(fill=tk.BOTH, expand=True)

        lbl2 = tk.Label(frame2, text="Info", width=6)
        lbl2.pack(side=tk.LEFT, anchor=tk.N, padx=5, pady=5)

        self._personInfo = tk.Text(frame2, width=20, height=10)
        self._personInfo.pack(fill=tk.BOTH, pady=5, padx=5, expand=True)

        frame3 = tk.Frame(self, padx=5, pady=5, borderwidth=1)
        frame3.pack(fill=tk.X, expand=True)
        cancelButton = tk.Button(frame3, text ="cancel",command=self.cancel)
        cancelButton.pack(side=tk.RIGHT)
        self._okButton = tk.Button(frame3, text ="ok",command=self.ok)
        self._okButton.pack(side=tk.RIGHT)
        self._okButton.config(state=tk.DISABLED)

        # check state of ok button
        self.enableEntry(0,0,0)

    def cancel(self):
        self.destroy();

    def ok(self):
        sql = 'INSERT INTO persons (name, info) VALUES (?,?)'
        values = (self._personName.get(), self._personInfo.get(1.0,tk.END))
        dbAnnot.db.execute(sql, values)
        dbAnnot.conn.commit()

        self.signalAdded()
        self.destroy()

    def enableEntry(self, var, index, mode):
        if self._personName.get()=="":
            self._okButton.config(state=tk.DISABLED)
        else:
            self._okButton.config(state=tk.NORMAL)


