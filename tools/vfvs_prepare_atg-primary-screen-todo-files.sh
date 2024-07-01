#!/bin/sh

#Checking the input arguments
usage="Usage: vfvs_prepare_atg-primary-screen-todo-files.sh <tranche scoring method> <size 1> <size 2> ...

Description: Preparing the folders for the ATG Primary Screens. For each docking scenario, and each specified screening size, one ATG Primary Screen folder will be created. The ATG Prescreen has to be postprocessed (with the command vfvs_postprocess_atg-prescreen.sh) before running this command with the same screening sizes. 

Arguments:
    <tranche_scoring_mode: dimension_averaging, tranche_min_score or tranche_ave_score
    <size N>: Number of ligands that should be screened in the ATG Primary Screen. Multiple sizes can be spcified if multiple ATG Primary Screens are planned to be run with different screening sizes. N is typically set to 10000000 (10M) or 100000000 (100M)
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
tranche_scoring_mode=$1
echo "Tranche scoring mode: ${tranche_scoring_mode}"

# Getting the score averages for each tranche
if [ "${tranche_scoring_mode}" == "dimension_averaging" ]; then
  for ds in $(cat ../workflow/config.json  | jq -r ".docking_scenario_names" | tr "," " " | tr -d '"\n[]' | tr -s " ")
  inputfile=${ds}.ranking.subset-1.csv.gz
  echo "Generating the dimension averaged tranche scores for docking scenario ${ds} and stored it in ../output-files/${ds}.dimension-averaged-activity-map.csv ..."
    for i in {0..17}; do
      for a in {A..F}; do
        echo -n "${i},${a},"
        zgrep -E "^.{$i}$a" ${inputfile} | awk -F ',' '{ total += $NF; count++ } END { print total/count }' || echo
      done
    done | sed "1i\Tranche,Class,Score" | tee ${ds}.dimension-averaged-activity-map.csv &
  done
fi
wait

# Generating new todo files for the ATG Primary Screens
# requires conda
if [ "${tranche_scoring_mode}" == "dimension_averaging" ]; then
  for size in ${@:2}; do
    for file in *dimension-averaged-activity-map.csv; do
      echo "Generating the todo file for the ATG Primary Screens for docking scenario ${file//.*} with ${size} ligands and storing it in ../output-files/${file/.*}.todo.$size ..."
      echo python ../tools/templates/create_todofile_atg-primaryscreen.py $file ~/Enamine_REAL_Space_2022q12.collections.parquet ~/Enamine_REAL_Space_2022q12.tranches.parquet ${tranche_scoring_mode} ${file/.*}.todo.$size $size
    done
  done | parallel -j 10
elif [[ "${tranche_scoring_mode}" == "tranche_min_score" ]] ||  [[ "${tranche_scoring_mode}" == "tranche_ave_score" ]] ; then
  for size in ${@:2}; do
    for file in *ranking.subset-1.csv.gz; do
      echo "Generating the todo file for the ATG Primary Screens for docking scenario ${file//.*} with ${size} ligands and storing it in ../output-files/${file/.*}.todo.$size ..."
      echo python ../tools/templates/create_todofile_atg-primaryscreen.py $file ~/Enamine_REAL_Space_2022q12.collections.parquet ~/Enamine_REAL_Space_2022q12.tranches.parquet ${tranche_scoring_mode} ${file/.*}.todo.$size $size
    done
  done | parallel -j 10
fi
wait

cd ../tools
