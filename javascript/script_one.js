// array stored in data
var fs = require('fs')
fs.readFile('list_entrie.json', 'utf8', function (err,data) {
  if (err) {
    return console.log(err);
  }
  	//console.log(data);
});

const hasStinName = fs.filter(entry => {
  return entry.value === 'Johns4';
})
console.log(hasStinName)
