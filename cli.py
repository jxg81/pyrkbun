"""CLI Interface to pyrkbun
"""
#! /usr/local/bin/python
import json
import argparse

import pyrkbun
from pyrkbun.const import ApiError, ApiFailure

SUPPORTED_DNS_RECORD_TYPES = {'A',
                              'AAAA',
                              'MX',
                              'CNAME',
                              'ALIAS',
                              'TXT',
                              'NS',
                              'SRV',
                              'TLSA',
                              'CAA'}

def run_ping(args: argparse.Namespace) -> str:
    """Run Ping"""
    result: dict = pyrkbun.ping(args.v4)
    return json.dumps(result)

def run_pricing(args: argparse.Namespace) -> str: # pylint: disable = unused-argument
    """Run Picing"""
    result: dict = pyrkbun.pricing.get()
    return json.dumps(result)

def run_ssl(args: argparse.Namespace) -> str:
    """Run SSL"""
    result: dict = pyrkbun.ssl.get(args.domain)
    return json.dumps(result)

def run_dns(args: argparse.Namespace) -> str:
    """Run DNS"""
    try:
        command: str = args.command
    except AttributeError:
        return 'Please choose from get, create, edit, delete, or restore'

    domain: str = args.domain
    record_id: str = args.id
    record_type: str = args.type
    name: str = args.name
    content: str = args.content
    ttl: str = args.ttl
    priority: str = args.priority
    notes: str = args.notes

    if command in ('create', 'edit'):
        record = {'name': name,
                  'type': record_type,
                  'content': content,
                  'ttl': ttl,
                  'prio': priority,
                  'notes': notes}
    try:
        if command == 'get':
            if record_id:
                records = pyrkbun.dns.get_records(domain, record_id=record_id)
            elif name and record_type:
                records = pyrkbun.dns.get_records(domain, record_type, name)
            else:
                records = pyrkbun.dns.get_records(domain)

            result = []
            for record in records:
                modified_record = record.__dict__
                modified_record['type'] = modified_record.pop('record_type')
                modified_record['id'] = modified_record.pop('record_id')
                modified_record.pop('domain', None)
                result.append(modified_record)

        elif command == 'create':
            result = pyrkbun.dns.create_record(domain, record)

        elif command == 'edit':
            if record_id:
                result = pyrkbun.dns.edit_record(domain, record, record_id=record_id)
            elif name and record_type:
                result = pyrkbun.dns.edit_record(domain, record, record_type, name)
            else:
                return 'Please set value for either id OR name and type'

        elif command == 'delete':
            if record_id:
                result = pyrkbun.dns.delete_record(domain, record_id=record_id)
            elif name and record_type:
                result = pyrkbun.dns.delete_record(domain, record_type, name)
            else:
                return 'Please set value for either id OR name and type'

    except (ApiError, ApiFailure) as error:
        return f'API Error -> {error.message}'

    return json.dumps(result)

def run_dns_bulk(args: argparse.Namespace): # pylint: disable = too-many-locals
    """Run DNS Bulk
    flush: Delete ALL existing records and load records from provided file
    merge: Update existing records and add new records if they do not yet exist.
        Records not specified in the file will remain unchanged. Existing records
        must include the ID
    add: Add all records in the provided file
    """
    domain: str = args.domain
    input_file: str = args.input
    output_file: str = args.output
    mode: str = args.mode
    created: dict = {'SUCCESS': [], 'FAILURE': []}
    edited: dict = {'SUCCESS': [], 'FAILURE': []}
    deleted: dict = {'SUCCESS': [], 'FAILURE': []}
    not_found: list = []

    def create_records(records: list):
        for record in records:
            record.pop('domain', None)
            record.pop('id', None)
            try:
                result = pyrkbun.dns.create_record(domain, record)
            except (ApiError, ApiFailure) as error:
                created['FAILURE'].append({'error': error.message, 'record': record})
                continue
            record.update({'id': str(result['id'])})
            created['SUCCESS'].append({'result': result, 'record': record})

    def delete_records(records: list):
        for record in records:
            try:
                result = pyrkbun.dns.delete_record(domain, record_id=record['id'])
            except (ApiError, ApiFailure) as error:
                deleted['FAILURE'].append({'result': error.message, 'record': record})
                continue
            deleted['SUCCESS'].append({'result': result, 'record': record})

    def edit_records(records: list):
        for record in records:
            try:
                result = pyrkbun.dns.edit_record(domain, record, record_id=record['id'])
            except (ApiError, ApiFailure) as error:
                edited['FAILURE'].append({'result': error.message, 'record': record})
                continue
            edited['SUCCESS'].append({'result': result, 'record': record})


    with open(input_file, 'r', encoding='utf8') as file:
        user_provided_records = json.load(file)

    run_dns_args = argparse.Namespace(domain=domain,
                                      command='get',
                                      id='', name='',
                                      type='',
                                      content='',
                                      ttl='',
                                      priority='',
                                      notes='')

    existing_records: dict = json.loads(run_dns(run_dns_args))
    print(existing_records)


    if mode == 'flush':
        delete_records(existing_records)
        create_records(user_provided_records)

    if mode == 'add':
        create_records(user_provided_records)

    if mode == 'merge': # pylint: disable = too-many-nested-blocks
        to_edit = []
        to_create = []
        for user_record in user_provided_records:
            # If the id key is present then it should be cheked for editing
            # if not, it should be created (fall through to first else)
            if user_record.get('id') is not None:
                # If the id key is present, but has no value, then assume
                # it should be created as well (fall through to nested else)
                if len(user_record['id']) != 0:
                    for exist_record in existing_records:
                        # If the Id values match between an existing and
                        # and user provided record then we need to edit it
                        if exist_record['id'] == user_record['id']:
                            to_edit.append(user_record)
                else:
                    to_create.append(user_record)
            else:
                to_create.append(user_record)
        # If after the above comparison if the record does not appear in
        # to_create or to_edit, then the ID must have been provided and
        # it must be incorrect
        for user_record in user_provided_records:
            if user_record not in to_create and user_record not in to_create:
                not_found.append(user_record)
        # create and edit records as required
        create_records(to_create)
        edit_records(to_edit)

    result = {'CREATED': created, 'EDITED': edited, 'DELETED': deleted, 'NOT_FOUND': not_found}

    with open(output_file, 'a+', encoding='utf8') as file:
        json.dump(result, file)

def main():
    """"Operate pyrkbun from the command line"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='CLI interface to the pyrkbun python library')

    parser.add_argument('-v', action='count', default=0, help='Set output verbosity')

    pyrkbun_subparser = parser.add_subparsers(help='Pyrkbun Functions')

    ping = pyrkbun_subparser.add_parser('ping', help='Poll API and return IP address')
    ping.set_defaults(func=run_ping)
    ping.add_argument('-v4', action='store_true', help='Force IPv4 Only')

    pricing = pyrkbun_subparser.add_parser('pricing', help='Retrieve pricing information')
    pricing.set_defaults(func=run_pricing)

    ssl = pyrkbun_subparser.add_parser('ssl', help='Retrieve SSL bundle if available')
    ssl.set_defaults(func=run_ssl)
    ssl.add_argument('domain', help='Target domain name')

    dns = pyrkbun_subparser.add_parser('dns', help='Operate DNS records')
    dns.set_defaults(func=run_dns)
    dns.add_argument('domain', help='Target domain')

    dns_subparser = dns.add_subparsers()

    get = dns_subparser.add_parser('get', help='Get a DNS record')
    get.set_defaults(command='get',
                     id='',
                     name='',
                     type='',
                     content='',
                     ttl='',
                     priority='',
                     notes='')
    get.add_argument('-id', help='Porkbun unique record ID')
    get.add_argument('-name', help='DNS record name', type=str)
    get.add_argument('-type', help='DNS record type',
                     type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    create = dns_subparser.add_parser('create', help='Create a DNS record')
    create.set_defaults(command='create',
                        id='',
                        name='',
                        type='',
                        content='',
                        ttl='',
                        priority='',
                        notes='')
    create.add_argument('-name', help='DNS record name', type=str)
    create.add_argument('-type', help='DNS record type',
                        type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    create.add_argument('-content', help='DNS record content', type=str)
    create.add_argument('-ttl', help='DNS record ttl', type=str)
    create.add_argument('-priority', help='DNS record priority', type=str)
    create.add_argument('-notes', help='DNS record notes', type=str)

    edit = dns_subparser.add_parser('edit', help='Edit a DNS record')
    edit.set_defaults(command='edit',
                      id='',
                      name='',
                      type='',
                      content='',
                      ttl='',
                      priority='',
                      notes='')
    edit.add_argument('-id', help='Porkbun unique record ID')
    edit.add_argument('-name', help='DNS record name', type=str)
    edit.add_argument('-type', help='DNS record type',
                      type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    edit.add_argument('-content', help='DNS record content', type=str)
    edit.add_argument('-ttl', help='DNS record ttl', type=str)
    edit.add_argument('-priority', help='DNS record priority', type=str)
    edit.add_argument('-notes', help='DNS record notes', type=str)

    delete = dns_subparser.add_parser('delete', help='Delete a DNS record')
    delete.set_defaults(command='delete',
                        id='',
                        name='',
                        type='',
                        content='',
                        ttl='',
                        priority='',
                        notes='')
    delete.add_argument('-id', help='Delete Record by record ID')
    delete.add_argument('-name', help='DNS record name', type=str)
    delete.add_argument('-type', help='DNS record type',
                        type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    bulk = dns_subparser.add_parser('bulk', help='Run bulk operations on DNS Service')
    bulk.set_defaults(func=run_dns_bulk, mode='update')
    bulk.add_argument('input', help='File containing JSON formatted DNS data')
    bulk.add_argument('output', help='File containing results of bulk operation')
    bulk.add_argument('-mode', help='Defaults to merge', choices={'flush', 'merge', 'add'})

    args = parser.parse_args()
    result = args.func(args)
    print(result)

if __name__ == "__main__":
    main()
