"""Wallet worker settings, shared by lifespan and configuration diagnostics."""
import os

def ledger_enabled():
    return os.getenv('AUTO_ANCHOR','false').strip().lower()=='true'

def wallet_enabled():
    # Preserve existing installations unless an independent setting is supplied.
    return os.getenv('AUTO_WALLET_STORAGE',os.getenv('AUTO_ANCHOR','false')).strip().lower()=='true'
