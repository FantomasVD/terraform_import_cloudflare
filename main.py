import CloudFlare
import os
import config as config

account_module_file = open('main.tf', 'w')
terraform_init = open('terraform_init.sh', 'w')

variable_api_token = '''
variable "api_token" {
    type = string
}
'''

cf = CloudFlare.CloudFlare(email=config.email, token=config.auth_token)

for account in cf.accounts():
    account_dir = account['name'].split("'")
    print(account_dir[0])
    os.mkdir(account_dir[0])
    
    account_module_name = account_dir[0].split('@')
    account_module_name = account_module_name[0].lower()
    account_module = '''
module "{module_name}" {{
    source = "./{dir_name}"
    api_token = "{api_token}"
}}
    '''.format(module_name = account_module_name, dir_name = account_dir[0], api_token=config.api_token)

    account_module_file.write(account_module)

    zone_module_file = open(account_dir[0]+'/'+'main.tf', 'w')

    account_variables_file = open(account_dir[0]+'/'+'variables.tf', 'w')
    account_variables_file.write(variable_api_token)


    for zone in cf.zones.get(params={'account.id':account['id'], 'per_page':100}):
        
        zone_module_name = zone['name'].replace('.', '_')
        
        if zone_module_name[0].isdecimal():
          zone_module_name = '_'+zone_module_name
        
        zone_module = '''
module "{module_name}" {{
    source = "./{dir_name}"
    api_token = "${{var.api_token}}"
}}
        '''.format(module_name = zone_module_name, dir_name = zone['name'])

        zone_module_file.write(zone_module)

        zone_dir = account_dir[0]+'/'+zone['name']

        os.mkdir(zone_dir)
        zone_variables_file = open(zone_dir+'/'+'variables.tf', 'w')
        zone_variables_file.write(variable_api_token)
        
        dns_file = open(zone_dir+'/'+'dns.tf', 'w')

        dns_provider = '''           
terraform {
  required_providers {
    cloudflare = {
      source = "cloudflare/cloudflare"
      version = "~> 3.0"
    }
  }
}

provider "cloudflare" {
  api_token = "${var.api_token}"
}            
            '''
        dns_file.write(dns_provider)
        
        for dns_record in cf.zones.dns_records.get(zone['id']):
            
          if dns_record['type'] == 'TXT' :
            resource_name=dns_record['name'].replace('.', '_')+'-'+dns_record['id']
          else:
            resource_name=dns_record['name'].replace('.', '_')+'-'+dns_record['content'].replace('.', '_')

          if resource_name[0].isdecimal():
                  resource_name = '_'+resource_name

          resource_name = resource_name.replace(' ', '-')
          resource_name = resource_name.replace('*', '')

          if 'priority' in dns_record:
             
              dns_resource = '''
resource "cloudflare_record" "{resource_name}" {{
  name     = "{name}"
  priority = {priority}
  proxied  = "{proxied}"
  ttl      = {ttl}
  type     = "{type}"
  value    = "{value}"
  zone_id  = "{zone_id}"
}}
        '''.format(resource_name=resource_name.replace('"', ''), name=dns_record['name'], priority=dns_record['priority'], proxied=str(dns_record['proxied']).lower(), ttl=dns_record['ttl'], type=dns_record['type'], value=dns_record['content'].replace('"', ''), zone_id=zone['id'])
    
          else:
            
              dns_resource='''
resource "cloudflare_record" "{resource_name}" {{
  name     = "{name}"
  proxied  = "{proxied}"
  ttl      = {ttl}
  type     = "{type}"
  value    = "{value}"
  zone_id  = "{zone_id}"
}}
        '''.format(resource_name=resource_name.replace('"', ''), name=dns_record['name'], proxied=str(dns_record['proxied']).lower(), ttl=dns_record['ttl'], type=dns_record['type'], value=dns_record['content'].replace('"', ''), zone_id=zone['id'])
    
          dns_file.write(dns_resource)
          terraform_init.write('terraform import module.{account_module_name}.module.{zone_module_name}.cloudflare_record.{resource_name}  {zone_id}/{dns_record_id}\n'.format(account_module_name=account_module_name, zone_module_name=zone_module_name, resource_name=resource_name.replace('"', ''), zone_id=zone['id'], dns_record_id=dns_record['id']))

        dns_file.close()
        zone_variables_file.close()

    zone_module_file.close()
    account_variables_file.close()
    
terraform_init.close()
account_module_file.close()