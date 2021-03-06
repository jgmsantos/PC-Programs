VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "ColFields"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit


Private colGeneric As ColFieldsGenericData
Private colLang As ColFieldsLangDependingData
Private mandatory As Collection

Private Sub LoadGeneric()
    Dim fn As Long
    Dim key As String
    Dim is_mandatory As String
    Dim reg As String
    Dim tag As String
    Dim genField As ClsFieldGenericData
    
    Set mandatory = New Collection
    fn = FreeFile
    Open App.Path + "\langs\fields.ini" For Input As fn
    
    Set colGeneric = New ColFieldsGenericData
    While Not EOF(fn)
        Input #fn, key, reg, tag, is_mandatory
        
        Set genField = New ClsFieldGenericData
        genField.is_mandatory = is_mandatory
        genField.key = key
        genField.reg = reg
        genField.tag = Replace(Replace(tag, "abcd", ""), "tl", "")
        Call colGeneric.add(key, genField)
        If is_mandatory <> "" And reg = "t" Then
            Call mandatory.add(genField.tag, CStr(mandatory.count))
        End If
    Wend
    Close fn
    
End Sub
Private Sub LoadLang(lang As String)
    Dim fn As Long
    Dim key As String
    Dim label As String
    Dim help As String
    Dim f As ClsFieldsLangDependingData
    
    fn = FreeFile
    Open App.Path + "\langs\" + lang + "_fields.ini" For Input As fn
    
    Set colLang = New ColFieldsLangDependingData
    While Not EOF(fn)
        Input #fn, key, label, help
        
        Set f = New ClsFieldsLangDependingData
        f.label = label
        f.key = key
        f.help = help
        
        Call colLang.add(key, f)
    Wend
    Close fn
End Sub
    
Sub SetLabels(lang As String)
    If colGeneric Is Nothing Then
    LoadGeneric
    End If
    Call LoadLang(lang)
End Sub
    
Function isA_mandatoryField(content As String, key As String) As String
    If (Len(colGeneric.item(key).is_mandatory) > 0) And (Len(content) = 0) Then
        isA_mandatoryField = colLang.item(key).label + vbCrLf
    End If
End Function
Function is_mandatory_at_least_one(content As String, key As String, content1 As String, key1 As String) As String
    If Len(content) = 0 And Len(content1) = 0 Then
        is_mandatory_at_least_one = colLang.item(key).label + " | " + colLang.item(key1).label + vbCrLf
    End If
End Function
Function getLabel(key As String) As String
    getLabel = colLang.item(key).label + colGeneric.item(key).is_mandatory
End Function

Function getHelp(key As String) As String
    getHelp = colLang.item(key).help
End Function
Function getMandatoryFields() As Collection
    Set getMandatoryFields = mandatory
End Function

