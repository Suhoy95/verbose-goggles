# WARNING !!!

These key-pairs and certificate are placed here only for testing and developing
purpose. Do not use them to provide security in any kind.

## Password of rootCA
```
HelloWorld
```

## Recreate rootCA.{key,crt}
```
make ca
```

## Create key and certificate signed by rootCA
```
make peer NAME=victor
```
It command will create next files:
```
victor/
  victor.key
  victor.crt
```
