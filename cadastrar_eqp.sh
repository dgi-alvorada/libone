#!/bin/bash
#Este script facilita o cadastros das cameras em uma nova implementacao
#Todas as cameras com arquivos de configuracao no diretorio cams serao cadastradas
search_dir=./cams
for file in "$search_dir"/*
do
  python3 cadastro_eqp.py "$file" 2
  python3 cadastro_eqp.py "$file" 4
done
