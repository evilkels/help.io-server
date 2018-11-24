const express = require('express');
const router = express.Router();
const exec = require('child_process').exec;

router.get('/', function(req, res, next) {
  res.send('get data');
});

/* POST heartrate information. */
router.post('/', async function (req, res, next) {
  const val = req.body;
  await executeCommand();
  console.log('request', val);
  res.status(400).json({"job": "done"});
})

async function executeCommand() {
  exec("ls -la", puts);
}
function puts(error, stdout, stderr) { console.log(stdout) }
module.exports = router;
