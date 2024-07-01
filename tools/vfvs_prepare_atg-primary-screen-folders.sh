#!/bin/sh

#Checking the input arguments
usage="Usage: vfvs_prepare_atg-primary-screen-folders.sh <jobname prefix> <size 1> <size 2> ...

Description: Preparing the folders for the ATG Primary Screens folders. For each docking scenario, and each specified screening size, one ATG Primary Screen folder will be created. Before running this script, the todo files have to be prepared. 

Arguments:
    <jobname prefix>: String that is used as prefix in the job output folders, e.g. abl1-vs1
    <size N>: Number of ligands that should be screened in the ATG Primary Screen. Multiple sizes can be spcified if multiple ATG Primary Screens are planned to be run with different screening sizes.
"

if [ "${1}" == "-h" ]; then
   echo -e "\n${usage}\n\n"
   exit 0
fi
if [ "$#" -le "1" ]; then
   echo -e "\nWrong number of arguments. At two arguments are required."
   echo -e "\n${usage}\n\n"
   echo -e "Exiting..."
   exit 1
fi

# Initial setup
cd ../output-files
prefix=$1

# Prepare next stage foldersparent_dir=$(basename $(dirname $(pwd)))
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Creating new VF directory (../../atg-primaryscreen_${size}_${ds}) for the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands"
    mkdir ../../atg-primaryscreen_${size}_${ds}
    cp -r ../.git* ../input-files/ ../tools/ ../../atg-primaryscreen_${size}_${ds}
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting job_name to ${prefix}-atg-primaryscreen_${size}_${ds}"
    sed -i "s/job_name=.*/job_name=${prefix}-atg-primaryscreen_${size}_${ds}/g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting data_collection_identifier to Enamine_REAL_Space_2022q12"
    sed -i "s|data_collection_identifier=.*|data_collection_identifier=Enamine_REAL_Space_2022q12|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting prescreen_mode to 0"
    sed -i "s|prescreen_mode=.*|prescreen_mode=0|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting docking_scenario_names to ${ds}"
    sed -i "s|docking_scenario_names=.*|docking_scenario_names=${ds}|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting docking_scenario_batchsizes to 1"
    sed -i "s|docking_scenario_batchsizes=.*|docking_scenario_batchsizes=1|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting docking_scenario_replicas to 1"
    sed -i "s|docking_scenario_replicas=.*|docking_scenario_replicas=1|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Edting the all.ctrl file of the ATG Primary Screen of docking scenrio ${ds} for ${size} ligands: Setting docking_scenario_programs to qvina02"
    sed -i "s|docking_scenario_programs=.*|docking_scenario_programs=qvina02|g" ../../atg-primaryscreen_${size}_${ds}/tools/templates/all.ctrl
  done
done
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  for size in ${@:2}; do
    echo "Copying the newly created todo file for docking scenario ${ds}: cp ../output-files/${ds}.todo.${size} ../../atg-primaryscreen_${size}_${ds}/tools/templates/todo.all"
    cp ../output-files/${ds}.todo.${size} ../../atg-primaryscreen_${size}_${ds}/tools/templates/todo.all
  done
done

# Changing to original directory
cd ../tools

#for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do for size in ${@:2}; do ( cd ../../atg-primaryscreen_${size}_${ds}/tools; ./vfvs_prepare_folders.py ) ;  done; done
#for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do for size in ${@:2}; do echo "( cd ../../atg-primaryscreen_${size}_${ds}/tools; ./vfvs_prepare_workunits.py )" ; done; done | parallel -j 10 --ungroup
#for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do for size in ${@:2}; do ( cd ../../atg-primaryscreen_${size}_${ds}/tools; ./vfvs_build_docker.sh ) ; done; done
#for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do for size in ${@:2}; do ( cd ../../atg-primaryscreen_${size}_${ds}/tools; ./vfvs_submit_jobs.py 1 500 ) ; done; done

