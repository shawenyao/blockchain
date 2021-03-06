# Demo of Proof-of-Work Blockchain

## Overview
* `bash/deploy` bash script to deploy the demo
* `bash/bcstartn` bash script to start the demo
* `bash/bcstop` bash script to stop the demo
* `python/blockchain.py` the blockchain class and functions
* `python/server.py` the flask server
* `input/node_ids.csv` the input file of port number and node id

## Instructions on AWS EC2 deployment
1. `cd ~`
2. `git clone https://github.com/shawenyao/blockchain.git`
3. `sudo ~/blockchain/bash/deploy`
4. `curl https://freedns.afraid.org/dynamic/update.php?xxxxxxxxxx`
5. Follow the guide (https://certbot.eff.org/) to request https certificate for the domain.
6. Add the following lines to `/etc/nginx/sites-available/default`:
```
location ~ "^/(5[\d]{3})/(.*)$" {
   proxy_pass http://0.0.0.0:$1/$2$is_args$args;
}
```
6. `~/blockchain/bash/bcstartn %number_of_nodes%`, where `%number_of_nodes%` should be replaced by a number no bigger than the number of rows in `input/node_ids.csv`

## Architecture
![](docs/architecture.png)

## References
Learn Blockchains by Building One

https://hackernoon.com/learn-blockchains-by-building-one-117428612f46

Learn Blockchains using Spreadsheets

https://medium.com/@vanflymen/learn-blockchains-using-spreadsheets-b97ad92b9b4d

How do peer-to-peer programs discover each other?

https://jameshfisher.com/2017/08/11/peer-to-peer-discovery/

Nested tables from json

http://bl.ocks.org/nautat/4085017

Read lines from a file into a Bash array

https://stackoverflow.com/questions/11393817/read-lines-from-a-file-into-a-bash-array

How to split a string into an array in Bash?

https://stackoverflow.com/questions/10586153/how-to-split-a-string-into-an-array-in-bash
