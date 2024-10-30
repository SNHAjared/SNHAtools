import tempfile
from Autodesk.Revit import DB,UI
from System import Guid
import json, os
import pyrevit
import pyrevit.forms
from datetime import datetime
from copy import deepcopy




# get model data from json file
MODEL_DATA_JSON_PATH = pyrevit.forms.pick_file(
        file_ext="json",
        files_filter="",
        init_dir=pyrevit.USER_DESKTOP,
        restore_dir=True,
        multi_file=False,
        unc_paths=False,
        title="Select JSON file exported from PowerShell"
)
with open(MODEL_DATA_JSON_PATH,"r") as json_file:
        model_data = json.load(json_file)
model_data_orig = deepcopy(model_data)




# 
def GetLinkCloudModelPath(link_name,model_data=model_data):
        for m in model_data:
                if m['model']['name'] == link_name:
                        return m['model']['path']




# check Revit version
uiapp = pyrevit.HOST_APP.uiapp
# if Revit version < 2022: we must save models locally and save modified json file,
#   then open Revit >= 2022 and rerun this script (with new json file) to initiate models to new hub.
if int(uiapp.Version.Number) < 2022:
    pass
# else if Revit version >= 2022: we can do the entire save-initiate process in one step
else:
    pass




tempDir=os.path.join(
        pyrevit.USER_DESKTOP,
        'Revit Models for Upgrade_{}'.format(
                str(datetime.today().strftime('%Y-%m-%d'))
                )
        )
if not os.path.exists(tempDir):
        os.mkdir(tempDir)  

# copy all models to new locations
for i,m in enumerate(model_data):
        # use project and model GUIDs to get cloud model path
        m['path'] = DB.ModelPathUtils.ConvertCloudGUIDsToCloudPath(
                region=DB.ModelPathUtils.CloudRegionUS,
                projectId=Guid(m['project']['guid']),
                modelId=Guid(m['model']['guid'])
                )
        # open model from cloud
        openOptions = DB.OpenOptions()
        openOptions.SetOpenWorksetsConfiguration(
                DB.WorksetConfiguration(
                        option=DB.WorksetConfigurationOption.CloseAllWorksets
                        )
                )
        m['uidoc'] = uiapp.OpenAndActivateDocument(
                modelPath=m['path'],
                openOptions=openOptions,
                detachAndPrompt=False
                )
        # make document handle
        m['doc'] = m['uidoc'].Document
        # save offline copy to temp folder
                                        
        tempFilePath = os.path.join(
                tempDir,
                m['model']['name']
                )
        tempSAO = DB.SaveAsOptions(
                Compact=True,
                MaximumBackups=1,
                OverwriteExistingFile=True
                )
        tempSAO.SetWorksharingOptions(
                DB.WorksharingSaveAsOptions(
                        SaveAsCentral=True
                        )
                )
        m['doc'].SaveAs(
                filepath=tempFilePath,
                options=tempSAO
                )
        model_data_orig[i]['local_path'] = tempFilePath

        # save back to cloud in new account and/or project
        m['doc'].SaveAsCloudModel(
                accountId=Guid(m['copy_to']['account_id']),
                projectId=Guid(m['copy_to']['project_id']),
                folderId=m['copy_to']['folder_id'].replace("%3A",":"),
                modelName=m['model']['name']
                )
        # update model['path'] in case it changed
        m['path'] = m['doc'].GetCloudModelPath()

json_path = os.path.join(
        tempDir,
        'models.json'
        )

with open(json_path,'w') as json_file:
        json.dump(model_data_orig,json_file)

# # reload all linked models
# for m in model_data:
#         try:
#                 for link in DB.FilteredElementCollector(m['doc']).OfCategory(DB.BuiltInCategory.OST_RvtLinks).WhereElementIsElementType():
#                         link.LoadFrom(path=GetLinkCloudModelPath(link.Name))
#         except:
#                 print("Could not relink model: {}".format(m['model']['name']))