#!/usr/bin/env python
# coding: utf-8

# Arguments
# 1: Path to sparse screening output summary file (later folder)
# 2: Path to todo.all file of complete library
# 3: Path to todo.count file of complete library
# 4: Filename of local todo.file that will be generated
# 5: Target number of ligands for primary screen

# Imports and Settings
import pandas as pd
import copy
import os
import sys
from IPython.display import display, HTML

# Settings
pd.set_option('display.max_rows', 10)
display(HTML("<style>.container { width:100% !important; }</style>"))

# Enamine_REAL_Space_2022q12.todo.csv
df_ERS_todo = pd.read_csv(sys.argv[2])
df_ERS_count = pd.read_csv(sys.argv[3])

# Enamine_REAL_Space_2022q12_sparse.tranche-scores.csv
df_tranche_scores = pd.read_csv(sys.argv[1])
df_tranche_scores = df_tranche_scores.dropna()
df_tranche_scores = df_tranche_scores.reset_index(drop=True)

# Getting the minimum scores for each tranche
for n in range(0, 18):
    df_tranche_scores.loc[df_tranche_scores['Tranche'] == n,'Min'] = df_tranche_scores.loc[df_tranche_scores['Tranche'] == n].min()['Score']

# Getting the score difference relative to the minimum in each tranche
df_tranche_scores['Diff'] = df_tranche_scores['Score'] - df_tranche_scores['Min']

# Getting the initial tranche classes for each tranche
regex = ''
selected_classes = list(df_tranche_scores.loc[df_tranche_scores['Diff'] == 0, 'Class'])

# Dropping the uses tranche classes
df_tranche_scores = df_tranche_scores.drop(df_tranche_scores[df_tranche_scores.Diff == 0].index)


# Forming regex
for Tranche in range(0, 18):
        regex = regex + '[' + selected_classes[Tranche] + ']'

# Counting the ligands
ligands_selected = df_ERS_todo[df_ERS_todo.Tranche.str.contains(regex)]['LigandCount'].sum()

# Adding additional tranche classes
ligand_count_aim = int(os.fsencode(sys.argv[5]))

# Loop until we have enough ligands
while ligands_selected < ligand_count_aim:

    # Finding the minimum difference tranche class
    selected_class = df_tranche_scores[df_tranche_scores.Diff == df_tranche_scores.Diff.min()].head(1)
    #selected_class = df_tranche_scores[df_tranche_scores.Score == df_tranche_scores.Score.min()].head(1)

    # Dropping the selected tranche class
    df_tranche_scores = df_tranche_scores.drop(selected_class.index)

    # Re-indexing
    selected_class = selected_class.reset_index(drop=True)
    df_tranche_scores = df_tranche_scores.reset_index(drop=True)

    # Adding the new tranche class to regex of selected tranches
    added_classes = copy.deepcopy(selected_classes)
    selected_classes[selected_class.at[0,'Tranche']] = selected_classes[selected_class.at[0,'Tranche']] + selected_class.at[0,'Class']
    added_classes[selected_class.at[0,'Tranche']] = selected_class.at[0,'Class']

    # Reforming regex strings
    regex_previous = copy.deepcopy(regex)
    regex_added = ''
    regex = ''
    for Tranche in range(0, 18):
        regex = regex + '[' + selected_classes[Tranche] + ']'
    for Tranche in range(0, 18):
        regex_added = regex_added + '[' + added_classes[Tranche] + ']'

    # Calculating the number of ligands selected
    ligands_selected_previous = ligands_selected
    ligands_selected = df_ERS_count[df_ERS_count.Tranche.str.contains(regex)]['LigandCount'].sum()

    # Printing status
    print("")
    print("Previous tranche regex string: ", regex_previous)
    print("Added tranche regex string:    ", regex_added)
    print("Current tranche regex string:  ", regex)
    print("Current number of ligands:     ", ligands_selected)

# electing subset of the last added tranche to prevent overselection
print("Selecting subset of the last added tranche to prevent overselection")

# Copying the relevant rows
df_ERS_todo_previous = df_ERS_todo[df_ERS_todo.Tranche.str.contains(regex_previous)].copy()
df_ERS_todo_added = df_ERS_todo[df_ERS_todo.Tranche.str.contains(regex_added)].copy()

# Loop for adding ligands
index = 0
ligands_selected_current = ligands_selected_previous
df_ERS_todo_added['Selected'] = "no"
for ind in df_ERS_todo_added.index:

    # Adding ligands for next collection
    ligands_selected_current = ligands_selected_current + df_ERS_todo_added['LigandCount'][ind]

    # Marking collected as selected
    df_ERS_todo_added['Selected'][ind] = "yes"
    print("ligands_selected_current: ", ligands_selected_current)
    if ligands_selected_current >= ligand_count_aim:
        print("Reached target number of ligands: ", ligands_selected_current)
        print()
        break

# Saving to output file
print("Saving new todo file")
df_ERS_todo_previous["Collection"] = df_ERS_todo_previous["Collection"].astype(str)
df_ERS_todo_previous['Collection'] = df_ERS_todo_previous['Collection'].str.zfill(7)
df_ERS_todo_previous['Collection'] = df_ERS_todo_previous[['Tranche', 'Collection']].agg('_'.join, axis=1)
df_ERS_todo_added["Collection"] = df_ERS_todo_added["Collection"].astype(str)
df_ERS_todo_added['Collection'] = df_ERS_todo_added['Collection'].str.zfill(7)
df_ERS_todo_added['Collection'] = df_ERS_todo_added[['Tranche', 'Collection']].agg('_'.join, axis=1)
df_ERS_todo_previous[["Collection", "LigandCount"]].to_csv(sys.argv[4],index=False,header=False,sep=' ')
df_ERS_todo_added[df_ERS_todo_added.Selected == "yes"][["Collection", "LigandCount"]].to_csv(sys.argv[4],index=False,mode='a',header=False,sep=' ')
