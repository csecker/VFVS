#!/usr/bin/env python3

# Copyright (C) 2019 Christoph Gorgulla
# Copyright (C) 2024 Christopher Secker
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# This file is part of VirtualFlow.
#
# VirtualFlow is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# VirtualFlow is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VirtualFlow.  If not, see <https://www.gnu.org/licenses/>.

# ---------------------------------------------------------------------------

import boto3
from botocore.config import Config
import time
import argparse
import json
import os
import glob
import pandas as pd
import re
from tqdm import tqdm
from typing import Optional


def parse_config(filename):
  with open(filename, "r") as read_file:
      config = json.load(read_file)

  return config

def wait_for_athena_completion(athena_client, s3_client, response_to_wait, delete=1, desc="unknown"):

  finished_states = ['SUCCEEDED', 'FAILED', 'CANCELLED']

  print(f"Waiting on {desc} ({response_to_wait['QueryExecutionId']})")
  while True:

    response = athena_client.get_query_execution(
        QueryExecutionId=response_to_wait['QueryExecutionId']
    )

    time.sleep(0.5)

    if(response['QueryExecution']['Status']['State'] in finished_states):

      if(delete == 1 and response['QueryExecution']['Status']['State'] == "SUCCEEDED"):
        # remove the old data
        obj_parts = response['QueryExecution']['ResultConfiguration']['OutputLocation'].split("/")
        obj_combined = "/".join(obj_parts[3:])

        del_response = s3_client.delete_object(
          Bucket=obj_parts[2],
          Key=obj_combined
        )

      break

  return response


def get_top_results_slurm_csv(docking_scenario_output_folder):
  files = glob.glob(os.path.join(docking_scenario_output_folder, 'csv', '*', '*.csv.gz'))

  if len(files) < 1:
      print(f"No results in {docking_scenario_output_folder} found, exiting...")
      return

  df_workunits = []
  pattern = re.compile(r'csv/(\d+)/(\d+)\.csv\.gz')

  for f in tqdm(files, desc='Collecting results', unit=' files'):
      match = pattern.search(f)
      if match:
          workunit = int(match.group(1))
          task = int(match.group(2))
      else:
          workunit = 0
          task = 0
      df_workunit = pd.read_csv(f, compression='gzip', sep=',')
      df_workunit.insert(loc=3, column='workunit', value=workunit)
      df_workunit.insert(loc=4, column='task', value=task)
      df_workunits.append(df_workunit)

  df_all = pd.concat(df_workunits, axis=0, ignore_index=True)
  df_all = df_all.sort_values(by='score_min', ascending=True).reset_index(drop=True)
  return df_all


def get_top_results_slurm_csv(
    docking_scenario_output_folder: str,
    top: Optional[int] = None,
    chunksize: int = 200_000,
):
    """
    Streaming top-k (smallest by 'score_min') over many CSV.GZ files, bounded memory.
    """
    files = glob.glob(os.path.join(docking_scenario_output_folder, 'csv', '*', '*.csv.gz'))

    if len(files) < 1:
        print(f"No results in {docking_scenario_output_folder} found, exiting...")
        return None

    pattern = re.compile(r'csv/(\d+)/(\d+)\.csv\.gz')

    keep_df = None
    have_score = False

    for f in tqdm(files, desc='Collecting results', unit=' files'):
        match = pattern.search(f)
        workunit = int(match.group(1)) if match else 0
        task = int(match.group(2)) if match else 0

        for chunk in pd.read_csv(f, compression='gzip', sep=',', chunksize=chunksize):
            chunk = chunk.assign(workunit=workunit, task=task)

            if 'score_min' not in chunk.columns:
                raise ValueError("Column 'score_min' not found in input CSVs.")
            have_score = True

            if top is None:
                if keep_df is None:
                    keep_df = chunk
                else:
                    keep_df = pd.concat([keep_df, chunk], axis=0, ignore_index=True)
            else:
                if len(chunk) > top:
                    chunk = chunk.nsmallest(top, 'score_min')
                if keep_df is None:
                    keep_df = chunk
                else:
                    keep_df = pd.concat([keep_df, chunk], axis=0, ignore_index=True)

                if len(keep_df) > int(top * 1.5):
                    keep_df = keep_df.nsmallest(top, 'score_min')

    if keep_df is None or (top is not None and len(keep_df) == 0):
        return None

    if not have_score:
        raise ValueError("No 'score_min' present in any file.")

    if top is not None:
        keep_df = keep_df.nsmallest(top, 'score_min')

    keep_df = keep_df.sort_values(by='score_min', ascending=True, kind='mergesort').reset_index(drop=True)
    return keep_df


def main():

  ctx = {}
  ctx['config'] = parse_config("../workflow/config.json")

  # Verify that there is a parquet output if batch system is AWS
  if 'parquet' not in ctx['config']['summary_formats'] and ctx['config']['batchsystem'] == 'awsbatch':
      print("In order to use the query on AWS runs, `parquet` must be a summary_format")
      exit(1)

  # Verify that there is a csv output if batch system is Slurm
  if 'csv.gz' not in ctx['config']['summary_formats'] and ctx['config']['batchsystem'] == 'slurm':
      print("In order to use the query on Slurm runs, `csv` must be a summary_format")
      exit(1)

  if ctx['config']['batchsystem'] != 'awsbatch' and ctx['config']['batchsystem'] != 'slurm':
    print("In order to use this query script, AWS or Slurm must be configured")
    exit(1)

  scenario_required = True
  scenario_default = None

  parser = argparse.ArgumentParser()

  if(len(ctx['config']['docking_scenarios_internal']) == 1):
    scenario_required = False
    scenario_default = list(ctx['config']['docking_scenarios_internal'].keys())[0]
    parser.add_argument('--scenario-name', action='store', type=str, required=scenario_required, default=scenario_default)
  else:
    parser.add_argument('--scenario-name', action='store', type=str, required=True)


  parser.add_argument('--download', action='store_true', required=False)



  parser.add_argument('--top', action='store', type=int, required=False)
  parser.add_argument('--chunksize', action='store', type=int, required=False, default=200000)
  args = parser.parse_args()



  botoconfig = Config(
    region_name = ctx['config']['aws_region'],
    retries = {
        'max_attempts': 50,
        'mode': 'standard'
    }
  )

  args_dict = vars(args)

  scenario = args_dict['scenario_name']

  if scenario not in ctx['config']['docking_scenarios_internal']:
    print(f"Scenario '{scenario}'' is not defined as part of this job")
    exit(1)

  if ctx['config']['batchsystem'] == 'awsbatch':

    table_name = f"{ctx['config']['job_name']}__{scenario}".replace("-", "_")

    database_name = f"{ctx['config']['aws_batch_prefix']}_vfvs"
    job_location = f"{ctx['config']['object_store_job_prefix_full']}/{scenario}/parquet"
    object_store_job_bucket = ctx['config']['object_store_job_bucket']
    scenario_info = ctx['config']['docking_scenarios_internal'][scenario]
    athena_location = f"s3://{object_store_job_bucket}/{ctx['config']['object_store_job_prefix_full']}/athena"



    client = boto3.client('athena', config=botoconfig)
    s3_client = boto3.client('s3', config=botoconfig)

    print("Running query in AWS Athena\n")


    # Create database

    create_database = f"""
    CREATE DATABASE IF NOT EXISTS {database_name}
      COMMENT 'VFVS output for Athena'
      LOCATION '{athena_location}';
    """
    athena_location_tmp = f"{athena_location}/tmp"

    create_db_response = client.start_query_execution(
        QueryString=create_database,
        QueryExecutionContext={
            'Catalog': 'AwsDataCatalog'
        },
        ResultConfiguration={
            'OutputLocation': athena_location_tmp
        }
    )

    response = wait_for_athena_completion(client, s3_client, create_db_response, desc="createdb if needed")
    if(response['QueryExecution']['Status']['State'] != "SUCCEEDED"):
      print(f"failed on createdb ({response['QueryExecution']['Status']['State']})")
      exit(1)

    drop_response = client.start_query_execution(
        QueryString=f"DROP TABLE IF EXISTS {table_name};",
        QueryExecutionContext={
            'Database': database_name,
            'Catalog': 'AwsDataCatalog'
        },
        ResultConfiguration={
            'OutputLocation': f'{athena_location}/tmp'
        }
    )

    response = wait_for_athena_completion(client, s3_client, drop_response, desc="dropping of old table")
    if(response['QueryExecution']['Status']['State'] != "SUCCEEDED"):
      print(f"failed on drop of old table ({response['QueryExecution']['Status']['State']})")
      exit(1)

    # Generate the table based on the configuration

    field_type = {
      'ligand': "STRING",
      'collection_key': "STRING",
      'scenario': "STRING",
      'score_average': "DOUBLE",
      'score_min': "DOUBLE"
    }

    fields = [ 'ligand', 'collection_key', 'scenario' ]
    fields.append("score_min")
    fields.append("score_average")

    for replica_index in range(int(scenario_info['replicas'])):
      fields.append(f"score_{replica_index}")
      field_type[f"score_{replica_index}"] = "DOUBLE"

    for attr in ctx['config']['print_attrs_in_summary']:
      fields.append(f"attr_{attr}")
      field_type[f"attr_{attr}"] = "STRING"


    generate = []
    for field_name in fields:
      generate.append(f"{field_name} {field_type[field_name]}")

    create_table_list = ",\n".join(generate)

    create_table = f"""
    CREATE EXTERNAL TABLE {table_name} (
        {create_table_list}
    )
    STORED AS PARQUET
    LOCATION 's3://{object_store_job_bucket}/{job_location}'
    tblproperties ("parquet.compression"="GZIP");
    """

    create_table_response = client.start_query_execution(
        QueryString=create_table,
        QueryExecutionContext={
            'Database': database_name,
            'Catalog': 'AwsDataCatalog'
        },
        ResultConfiguration={
            'OutputLocation': f'{athena_location}/tmp'
        }
    )

    response = wait_for_athena_completion(client, s3_client, create_table_response, desc="create table")
    if(response['QueryExecution']['Status']['State'] != "SUCCEEDED"):
      print(f"failed on create of table ({response['QueryExecution']['Status']['State']})")
      exit(1)


    if 'top' in args_dict and args_dict['top'] != None:
      top_string = f"limit {args_dict['top']}"
    else:
      top_string = ""

    select_statement = f"SELECT *,\"$path\" from {table_name} ORDER BY score_min ASC {top_string};"

    select_response = client.start_query_execution(
        QueryString=select_statement,
        QueryExecutionContext={
            'Database': database_name,
            'Catalog': 'AwsDataCatalog'
        },
        ResultConfiguration={
            'OutputLocation': f'{athena_location}',
        }
    )

    response = wait_for_athena_completion(client, s3_client, select_response, delete=0, desc="query")

    print("")
    print(f"STATUS: {response['QueryExecution']['Status']['State']}")
    print(f"Output location: {response['QueryExecution']['ResultConfiguration']['OutputLocation']}")


    if args_dict['download'] == True:
      if 'top' in args_dict and args_dict['top'] != None:
        os.system(f"aws s3 cp {response['QueryExecution']['ResultConfiguration']['OutputLocation']}" + " " + "../output-files/" + scenario + ".ranking." + "top-" +  str(args.top) + ".csv")
      else:
        os.system(f"aws s3 cp {response['QueryExecution']['ResultConfiguration']['OutputLocation']}" + " " + "../output-files/" + scenario + ".ranking.complete.csv")

  elif ctx['config']['batchsystem'] == 'slurm':
    docking_scenario_output_folder = os.path.join('..', 'output-files', scenario)

    results = get_top_results_slurm_csv(
        docking_scenario_output_folder=docking_scenario_output_folder,
        top=args_dict.get('top'),
        chunksize=args_dict.get('chunksize') or 200000,
    )

    if isinstance(results, pd.DataFrame):
      status = "SUCCEEDED"
    else:
      status = "FAILED"

    print("")
    print(f"STATUS: {status}")
    print(f"Output location: {docking_scenario_output_folder}")
    print("Preview:")
    print("")
    if 'top' in args_dict and args_dict['top'] != None:
      print(results.head(args.top).reset_index(drop=True))
    else:
      print(results.reset_index(drop=True))

    if args_dict['download'] == True and isinstance(results, pd.DataFrame):
      if 'top' in args_dict and args_dict['top'] != None:
        output_file = docking_scenario_output_folder + "." + ".ranking.top-" + str(args.top) + ".csv"
        results = results.head(args.top)
      else:
        output_file = docking_scenario_output_folder + ".ranking.complete.csv"

      results.to_csv(output_file, header=True, index=None)
      print(f"Output saved to {output_file}")
      print("")

    else:
      print("Add --download flag to save output")
      print("")

  else:
        print("Batch system not known, must be either 'awsbatch' or 'slurm")
        exit(1)

if __name__ == '__main__':
    main()
