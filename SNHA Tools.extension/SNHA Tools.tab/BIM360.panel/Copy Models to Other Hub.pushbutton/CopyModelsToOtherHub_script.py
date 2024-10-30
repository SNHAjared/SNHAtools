from Autodesk.Revit import DB, UI
from System import Guid
import os, re, json
import pyrevit
import pyrevit.forms


uiapp = pyrevit.HOST_APP.uiapp


def GetLinkCloudModelPath(link_name, model_data_list):
    for m in model_data_list:
        if m['model']['name'] == link_name:
            return m['model']['path']


def UrlToFolderId(url):
    if "b360.autodesk.com" in url:
        patt = re.compile('(?<=folders/)(.*)(?=/detail)')
        folderId = re.findall(patt,url)[0]
    elif "acc.autodesk.com" in url:
        patt = re.compile('(?<=folderUrn=)(.*)(?=&viewModel=)')
        folderId = re.findall(patt,url)[0].replace('%3A',':')
    else:
        raise "Could not find FolderId in supplied url: {}".format(url)
    
    return folderId


if uiapp.Application.VersionNumber < 2022:
    raise "This script only works in Revit 2022+."
else:
    MODEL_DATA_JSON_PATH = pyrevit.forms.pick_file(
        file_ext="json",
        files_filter="",
        init_dir=pyrevit.USER_DESKTOP,
        restore_dir=True,
        multi_file=False,
        unc_paths=False,
        title="Select JSON file exported from PowerShell"
    )

    if MODEL_DATA_JSON_PATH:
        with open(MODEL_DATA_JSON_PATH, "r") as json_file:
            model_data = json.load(json_file)
        # handle case where model_data json contains <2 models
        if type(model_data) != list:
            model_data = [model_data]

        # copy all models to new locations
        for m in model_data:
            # use project and model GUIDs to get cloud model path
            m['path'] = DB.ModelPathUtils.ConvertCloudGUIDsToCloudPath(
                region=DB.ModelPathUtils.CloudRegionUS,
                projectGuid=Guid(m['project']['guid']),
                modelGuid=Guid(m['model']['guid'])
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
                pyrevit.USER_SYS_TEMP,
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
            # save back to cloud in new account and/or project
            if 'folder_url' in m['copy_to']:
                folderId=UrlToFolderId(m['copy_to']['folder_url'])
            elif 'folder_id' in m['copy_to']:
                folderId=m['copy_to']['folder_id'].replace('%3A',':')

            m['doc'].SaveAsCloudModel(
                accountId=Guid(m['copy_to']['account_id']),
                projectId=Guid(m['copy_to']['project_id']),
                folderId=folderId,
                modelName=m['model']['name']
            )
            # update model['path'] in case it changed
            m['path'] = m['doc'].GetCloudModelPath()

        # reload all linked models
        for m in model_data:
            for link in DB.FilteredElementCollector(m['doc']).OfCategory(DB.BuiltInCategory.OST_RvtLinks).WhereElementIsElementType():
                link.LoadFrom(path=GetLinkCloudModelPath(link.Name))
