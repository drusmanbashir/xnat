
# %%
from xnat.object_oriented import *
if __name__ == "__main__":
    
# %%
    c,_ = login()
    proj_title='nodes'
    proj = Proj(proj_title)
    subs = proj.subjects()
    # df= proj.create_report()
    # proj.export_nii(symlink=True,overwrite=True,ensure_fg=True,label=label)

#NOTE:: Get projects
    projs=  c.select.projects().get()
# %%
    sub = subs[0]
    sub = Subj(sub)
    sub.test= 'test'
    sub.get_info()
# %%
    sub.attrs.set("ethnicity","test")

    subject_id = sub.id()
    columns = ['xnat:subjectData/PROJECT',
               'xnat:subjectData/SUBJECT_ID',
               'xnat:subjectData/INSERT_DATE',
               'xnat:subjectData/GENDER_TEXT',
               'xnat:subjectData/ETHNICITY',]

    dt = 'xnat:subjectData'
    data = c.select(dt, columns=columns).all().data
    c._subjectData = data
    data = [e for e in data if e['subject_id'] == subject_id][0]

# %%

    c.inspect.datatypes('xnat:projectData')
    c.inspect.datatypes('xnat:experimentData')
    c.inspect.datatypes('xnat:ctSessionData')

# %%
    constraints = [
                  ('xnat:subjectData/PROJECT', '=', 'nodes'),
                   'OR',

                   [('xnat:subjectData/AGE','>','14'),

                    'AND'

                    ]

                   ]
# %%
    aa=    c.select('xnat:subjectData',
             [
             'xnat:subjectData/SUBJECT_ID'
             ]
                    ).where(constraints)
# %%
    const = [
        ('xnat:projectData/name','=','lidc2')
    ]
    aa=    c.select('xnat:projectData',
             [
            # 'xnat:projectData/name',
             'xnat:projectData/keywords'
             ]
                    ).where(const)

    print(aa.as_list())

    print(aa.data[0]['keywords'])

# %%
    aa =c.select('xnat:ctSessionData',

               ['xnat:subjectData/SUBJECT_ID',
                

                'xnat:subjectData/AGE']

        ).where(constraints)
# %%
