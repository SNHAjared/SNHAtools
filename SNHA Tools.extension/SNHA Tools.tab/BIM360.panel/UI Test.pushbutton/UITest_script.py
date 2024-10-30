import pyrevit
from pyrevit import revit, forms

# ops = {'Sheet Set A': ['viewsheet1', 'viewsheet2', 'viewsheet3'],
#        'Sheet Set B': ['viewsheet4', 'viewsheet5', 'viewsheet6']
#        }
# res = forms.SelectFromList.show(
#     ops,
#     multiselect=True,
#     group_selector_title='Sheet Sets',
#     button_name='Select Sheets'
#     )

forms.ask_for_string()