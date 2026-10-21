Ansible code
============

The folder `add-demo-synth-data` contains the ansible code that was used to deploy on the SSH test server. The whole folder was part of the Github repo from `https://github.com/DANS-KNAW/dans-core-systems`. 
Where is was located at: `provisioning/patches/add-demo-synth-data`.

The deployment command for the development setup was:
```
deploy.py --playbook provisioning/patches/add-demo-synth-data/add.yml dev_ssh
```

On the test server we needed to provide the username via the `-u` option, and the host name was `test_ssh`. 
