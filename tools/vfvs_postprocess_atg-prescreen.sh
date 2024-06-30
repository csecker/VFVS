#!/bin/sh

#Checking the input arguments
usage="Usage: vfvs_postprocess_atg-prescreen.sh

Description: Postprocessing the ATG Prescreen, and preparing the todo files for the ATG Primary Screens. The script can handle multiple docking scenarios in the ATG Prescreen.

"

if [ "${1}" == "-h" ]; then
   echo -e "\n${usage}\n\n"
   exit 0
fi
if [ "$#" -e "0" ]; then
   echo -e "\nWrong number of arguments. At least one screening size required."
   echo -e "\n${usage}\n\n"
   echo -e "Exiting..."
   exit 1
fi

# Output-files directory
mkdir -p ../output-files
cd ../output-files

# Getting the CSV files with the ligand rankings
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  ../tools/vfvs_get_top_results.py --scenario-name $ds --download
done

# Cleaning the CSV files
for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " "); do
  awk 'BEGIN { FS=OFS="," } { gsub("_", ",", $2); print }' ${ds}.csv | awk -F ',' '{print $2","$3","$1","$5}' | sed "1s/.*/Tranche,Collection,LigandVFID,ScoreMin/" | tr -d '"' > ${ds}.clean.csv
done

wait 

cd ../tools
