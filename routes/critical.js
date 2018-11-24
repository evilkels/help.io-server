const express = require('express');
const router = express.Router();
const exec = require('child_process').exec;

const spawn = require("child_process").spawn;

const GROUP_ID = `0xc123`;
const patients = {
  '0x0001': {
    name: 'Bob',
    sector: 'S1',
  },
  '0x0002': {
    name: 'Anna',
    sector: 'S2',
  },
};

const doctors = {
  '0x0003': {
    name: 'Doctor 1',
  },
  '0x0004': {
    name: 'Doctor 2',
  },
};

const BT_EXEC = 'python3 execute.py model 0 0x0000'
const BROADCAST_MSG = (nodeId, pId, pSector, pCritical) => {
  return `${BT_EXEC} 0xfbf105 ${nodeId} 0 0${pId}${pSector}${pCritical}`
}

/* POST heartrate information. */
router.post('/:patientId/setup', async (req, res, next) => {
  const { patientId } = req.params;

  try {
    const command = BROADCAST_MSG(
      patientId, patientId, patients[patientId].sector, 0
    );
    console.log('/:patientId/setup')
    console.log(command)
    await executeCommand(command, { cwd: process.cwd() });
    return res.status(204).json();
  } catch (error) {
    console.error(error)
    return res.status(404).json();
  }
})

router.post('/:patientId/critical', async (req, res, next) => {
  const { patientId } = req.params;

  try {
    const command = BROADCAST_MSG(
      GROUP_ID, patientId, patients[patientId].sector, 1
    );
    console.log('/:patientId/critical')
    console.log(command)
    await executeCommand(command, { cwd: process.cwd() });
    return res.status(204).json();
  } catch (error) {
    console.error(error)
    return res.status(404).json();
  }
})

function executeCommand(command, options) {
  return new Promise((resolve, reject) => {
    exec(command, options, (error, out) => {
      if (error) {
        return reject(error);
      }

      console.log('out', out);
      return resolve(out);
    });
  })
}

module.exports = router;
