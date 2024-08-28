## To run into docker
```
docker build -t datafed-app . 
``` 

```
docker run -p 5006:5006 datafed-app
```
## Modify Env accordingly

## To run locally 

### Install requirements.txt
```
pip install -r requirements.txt
```
### Run App.py
```

panel serve app.py --autoreload --port 5006

```