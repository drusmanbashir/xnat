#!/bin/bash
# http -a admin:admin --form PUT http://localhost:8080/xnat-web-1.8.8/data/projects/bosniak/config/applet/default-subject-labeling-scheme dicom_patient_id
# http -a admin:admin --form PUT http://localhost:8080/xnat-web-1.8.8/data/projects/bosniak/config/applet/default-subject-labeling-scheme dicom_patient_id

#
# http -a admin:admin PUT http://localhost:8080/xnat-web-1.8.8/data/config/scan-quality/labels?inbody=true @tmp.txt
# http -a admin:admin  PUT http://localhost:8080/xnat-web-1.8.8/xapi/dicom_mappings/update/  @code_mapping


# http -a admin:admin --form GET http://localhost:8080/xnat-web-1.8.8/data/projects/litqsmall/subjects/10/experiments/10_CT_1/scans/3 
# http -a admin:admin  GET http://localhost:8080/xnat-web-1.8.8/data/projects/tmp/subjects 
# http -a admin:admin  GET http://localhost:8080/xnat-web-1.8.8/xapi/custom-fields/projects/litqsmall/fields
# http -a admin:admin  GET http://localhost:8080/xnat-web-1.8.8/xapi/dicom_mappings/
# http -a admin:admin GET http://localhost:8080/xnat-web-1.8.8/data/config/scan-quality/labels
# http -a admin:admin GET http://localhost:8080/xnat-web-1.8.8/data/projects/subjects/
# http -a admin:admin  --download http://localhost:8080/xnat-web-1.8.8/data/projects/litq/subjects/11/experiments/XNAT_E00182/scans/4/resources/NIFTI/files --output
# http -a admin:admin  --download http://localhost:8080/xnat-web-1.8.8/data/projects/litq/subjects/11/resources/NIFTI/files?format=zip
# http -a admin:admin  GET http://localhost:8080/xnat-web-1.8.8/data/projects/tmp/subjects/20/experiments/
# http -a admin:admin  POST http://localhost:8080/xnat-web-1.8.8/data/services/refresh/catalog?resources=/archive/experiments//resources/IMAGE

# http -a admin:admin  POST http://localhost:8080/xnat-web-1.8.8/data/services/refresh/catalog?resource=/archive/projects/litq/subjects/60/experiments/60_CT_1/scans/4/resources/MASK
# http -a admin:admin  POST http://localhost:8080/xnat-web-1.8.8/data/services/refresh/catalog?resource=/archive/experiments/XNAT_E00217
http -a admin:admin  PUT http://localhost:8080/xnat-web-1.8.8/data/projects/litq/subjects/90?xsiType=xnat:subjectData/demographics[@xsi:type=xnat:demographicData]/race=test
