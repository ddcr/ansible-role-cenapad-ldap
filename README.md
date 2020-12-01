# Development and testing of Ansible role to install LDAP server

This is a development project to install and configure an LDAP 
server on a CentOS 7 server. We need to open the same user cluster 
accounts in other standalone computing servers, so it is important 
to centralize user/projects information.

I started by testing this role during development by using a homegrown 
 shell script (`manual-testing-env.bash`), that creates a docker container, 
 and then by executing the playbook `SetupCENAPAD-LDAP.yml`. 
I found out later that a more elegant way of doing this is using the
[molecule](https://molecule.readthedocs.io) tool.

> It seems that the combination `ansible` (*installed by rpm*) and `molecule`
> (*installed via pip3 install --user*) does not work. This seems to be related
> to a packaging "bug" [(see https://github.com/ansible-community/molecule/issues/2173)](https://github.com/ansible-community/molecule/issues/2173).
>  
> There are two temporary solutions:
>  
> - remove the flag `-s` from the header of `/usr/bin/ansible (#!/usr/bin/python3 -s)`
> - remove the ansible rpm and install molecule (`pip3 install molecule[docker]`)
>   inside a python virtualenv (eg. anaconda virtualenv). Ansible will be installed as
>   a dependency.
>  
> I give preference to the second option

