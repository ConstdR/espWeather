#!/bin/bash

command=''

for f in *.sqlite3
do
    headsql="echo $f ; echo 'select * from data order by timedate desc limit 10' | sqlite3 $f ; echo ;"
    command="$command $headsql"
done

watch -n 30 "$command"
