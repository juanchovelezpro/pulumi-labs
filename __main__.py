import pulumi 
from pulumi_aws_native import ec2, TagArgs

def create_subnets(subnets, vpc, routeTable):
    theSubnets = []
    for sub in subnets:
        subnetName = sub['name']
        az = sub['az']
        subnetCidr = sub['cidrBlock']
        subnet = ec2.Subnet(resource_name=subnetName, cidr_block=subnetCidr, availability_zone=az, vpc_id=vpc.id, tags=[TagArgs(key='Name', value=subnetName)])
        ec2.SubnetRouteTableAssociation(resource_name=f"srta-{subnetName}", route_table_id=routeTable.id, subnet_id=subnet.id)
        theSubnets.append(subnet)
        pulumi.export(f'{subnetName}-id', subnet.id)
    
    return theSubnets

# Config Vars      
config = pulumi.Config()
cVpc = config.require_object('vpc')
private_subnets = config.require_object('private-subnets')
public_subnets = config.require_object('public-subnets')
data_subnets = config.require_object('data-subnets')
aws = pulumi.Config('aws-native')
region = aws.require('region')

# VPC
vpcName = cVpc['name']
vpc = ec2.Vpc(resource_name=vpcName, cidr_block=cVpc['cidrBlock'], tags=[TagArgs(key='Name', value=vpcName)])
pulumi.export('vpc-id', vpc.id)

# IG
ig = ec2.InternetGateway(resource_name=f"ig-{vpcName}")
pulumi.export('ig-id', ig.id)
ec2.VpcGatewayAttachment(resource_name=f"ig-attachment-{vpcName}",vpc_id=vpc.id, internet_gateway_id=ig.id)

# Route Tables
publicRouteTable = ec2.RouteTable("public-route-table", vpc_id=vpc.id, tags=[TagArgs(key="Name", value="public-route-table")])
privateRouteTable = ec2.RouteTable("private-route-table", vpc_id=vpc.id, tags=[TagArgs(key="Name", value="private-route-table")])
dataRouteTable = ec2.RouteTable("data-route-table", vpc_id=vpc.id, tags=[TagArgs(key="Name", value="data-route-table")])
ec2.Route(resource_name="internet-route", destination_cidr_block="0.0.0.0/0", gateway_id=ig.id, route_table_id=publicRouteTable.id)

# Subnets
privateSubnets = create_subnets(private_subnets, vpc, privateRouteTable)
publicSubnets = create_subnets(public_subnets, vpc, publicRouteTable)
dataSubnet = create_subnets(data_subnets, vpc, dataRouteTable)

# NAT Gateway
elasticIP = ec2.Eip("eip-nat-gateway",network_border_group=region)
natGateway = ec2.NatGateway(resource_name=f"ng-{vpcName}", subnet_id=publicSubnets[0].id, allocation_id=elasticIP.allocation_id)
ec2.Route(resource_name="nat-internet-route", destination_cidr_block="0.0.0.0/0", nat_gateway_id=natGateway.id, route_table_id=privateRouteTable.id)