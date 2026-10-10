// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Independent prototype. Only hashes and opaque IDs, never private documents.
contract VerisLedger {
    address public immutable owner;
    mapping(address => bool) public writers;
    struct Record {
        bytes32 caseId;
        bytes32 documentHash;
        bytes32 evidenceHash;
        bytes32 parentRecordId;
        uint64 timestamp;
        uint8 outcome; // 1 = confirmed fraud, 2 = appeal upheld
    }
    mapping(bytes32 => Record) public records;
    event DecisionAnchored(bytes32 indexed recordId, bytes32 indexed caseId, bytes32 documentHash, bytes32 evidenceHash, bytes32 parentRecordId, uint64 timestamp, uint8 outcome);
    event WriterChanged(address indexed writer, bool allowed);
    constructor() { owner = msg.sender; writers[msg.sender] = true; }
    function setWriter(address writer, bool allowed) external {
        require(msg.sender == owner, "Owner only");
        require(writer != address(0), "Invalid writer");
        writers[writer] = allowed;
        emit WriterChanged(writer, allowed);
    }
    function anchor(bytes32 recordId, bytes32 caseId, bytes32 documentHash, bytes32 evidenceHash, bytes32 parentRecordId, uint64 timestamp, uint8 outcome) external {
        require(writers[msg.sender], "Authorized writer only");
        require(recordId != bytes32(0) && caseId != bytes32(0), "Invalid ID");
        require(documentHash != bytes32(0) && evidenceHash != bytes32(0), "Hashes required");
        require(records[recordId].timestamp == 0, "Record already exists");
        require(outcome == 1 || outcome == 2, "Unsupported outcome");
        require(timestamp > 0 && timestamp <= block.timestamp + 300, "Invalid timestamp");
        if (parentRecordId != bytes32(0)) {
            require(records[parentRecordId].caseId == caseId, "Parent must exist for case");
        }
        if (outcome == 2) {
            require(parentRecordId != bytes32(0), "Appeal requires prior finding");
            require(records[parentRecordId].outcome == 1, "Appeal parent must be confirmed");
        }
        records[recordId] = Record(caseId, documentHash, evidenceHash, parentRecordId, timestamp, outcome);
        emit DecisionAnchored(recordId, caseId, documentHash, evidenceHash, parentRecordId, timestamp, outcome);
    }
}
