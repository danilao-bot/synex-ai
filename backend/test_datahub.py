import urllib.request
import json
req = urllib.request.Request('http://localhost:8080/api/graphql', 
    data=json.dumps({'query': 'query { search(input: {type: DATASET, query: "*", start: 0, count: 5}) { searchResults { entity { urn } } } }'}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)
print(urllib.request.urlopen(req).read().decode('utf-8'))
