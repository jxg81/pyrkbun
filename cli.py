#! /usr/local/bin/python
import pyrkbun
import json
import argparse

from pyrkbun.const import ApiError

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

def run_ping(args):
    """Run Ping"""
    result = pyrkbun.ping(args.v4)
    return print(json.dumps(result))

def run_pricing(args):
    """Run Picing"""
    result = pyrkbun.pricing.get()
    return print(json.dumps(result))

def run_ssl(args):
    """Run SSL"""
    result = pyrkbun.ssl.get(args.domain)
    return print(json.dumps(result))

def run_dns(args):
    """Run DNS"""
    try:
        command = args.command
    except AttributeError:
        return print('Please choose from get, create, edit, delete')

    domain = args.domain
    record_id = args.id
    record_type = args.type
    name = args.name
    content = args.content
    ttl = args.ttl
    priority = args.priority
    notes = args.notes

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
                result.append(record.__dict__)

        elif command == 'create':
            result = pyrkbun.dns.create_record(domain, record)

        elif command == 'edit':
            if record_id:
                result = pyrkbun.dns.edit_record(domain, record, record_id=record_id)
            elif name and record_type:
                result = pyrkbun.dns.edit_record(domain, record, record_type, name)
            else:
                return print('Please set value for either id or name and type')

        elif command == 'delete':
            if record_id:
                result = pyrkbun.dns.delete_record(domain, record_id=record_id)
            elif name and record_type:
                result = pyrkbun.dns.delete_record(domain, record_type, name)
            else:
                return print('Please set value for either id or name and type')
    
    except ApiError as error:
        return print(f'Error -> {error.message}')
    
    return print(json.dumps(result))


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
    get.set_defaults(command='get', id='', name='', type='', content='', ttl='', priority='', notes='')
    get.add_argument('-id', help='Porkbun unique record ID')
    get.add_argument('-name', help='DNS record name', type=str)
    get.add_argument('-type', help='DNS record type', type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    create = dns_subparser.add_parser('create', help='Create a DNS record')
    create.set_defaults(command='create', id='', name='', type='', content='', ttl='', priority='', notes='')
    create.add_argument('-id', help='Porkbun unique record ID')
    create.add_argument('-name', help='DNS record name', type=str)
    create.add_argument('-type', help='DNS record type', type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    create.add_argument('-content', help='DNS record content', type=str)
    create.add_argument('-ttl', help='DNS record ttl', type=str)
    create.add_argument('-priority', help='DNS record priority', type=str)

    edit = dns_subparser.add_parser('edit', help='Edit a DNS record')
    edit.set_defaults(command='edit', id='', name='', type='', content='', ttl='', priority='', notes='')
    edit.add_argument('-id', help='Porkbun unique record ID')
    edit.add_argument('-name', help='DNS record name', type=str)
    edit.add_argument('-type', help='DNS record type', type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    edit.add_argument('-content', help='DNS record content', type=str)
    edit.add_argument('-ttl', help='DNS record ttl', type=str)
    edit.add_argument('-priority', help='DNS record priority', type=str)

    delete = dns_subparser.add_parser('delete', help='Delete a DNS record')
    delete.set_defaults(command='delete', id='', name='', type='', content='', ttl='', priority='', notes='')
    delete.add_argument('-id', help='Delete Record by record ID')
    delete.add_argument('-name', help='DNS record name', type=str)
    delete.add_argument('-type', help='DNS record type', type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
