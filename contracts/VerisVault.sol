// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Wallet-owned references to encrypted files. Files and private keys stay off-chain.
contract VerisVault {
    address public immutable writer;
    struct Document { address owner; bytes32 fileHash; string cid; bytes32 consentHash; uint256 registeredAt; }
    mapping(bytes32 => Document) private documents;
    event DocumentStored(bytes32 indexed id, address indexed owner, bytes32 fileHash, string cid, bytes32 consentHash);
    constructor() { writer = msg.sender; }
    function store(bytes32 id, address owner, bytes32 fileHash, string calldata cid, bytes32 consentHash) external {
        require(msg.sender == writer, "Unauthorized writer");
        require(documents[id].owner == address(0), "Already stored");
        require(id != bytes32(0) && owner != address(0) && fileHash != bytes32(0), "Invalid identity");
        require(bytes(cid).length > 0 && bytes(cid).length <= 100 && consentHash != bytes32(0), "Invalid evidence");
        documents[id] = Document(owner, fileHash, cid, consentHash, block.timestamp);
        emit DocumentStored(id, owner, fileHash, cid, consentHash);
    }
    function getDocument(bytes32 id) external view returns (Document memory) { return documents[id]; }
}
