"""Schéma NSL-KDD partagé (évite de recopier COLS / classes partout)."""

CLASSES = ["NORMAL", "DOS", "PROBE", "R2L", "U2R"]
NB_CLASSES = len(CLASSES)

COLS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate", "label", "difficulty",
]

CAT = ["protocol_type", "service", "flag"]

_DOS = {
    "back", "land", "neptune", "pod", "smurf", "teardrop", "apache2",
    "udpstorm", "processtable", "mailbomb", "worm",
}
_PROBE = {"satan", "ipsweep", "nmap", "portsweep", "mscan", "saint"}
_R2L = {
    "guess_passwd", "ftp_write", "imap", "phf", "multihop", "warezmaster",
    "warezclient", "spy", "xlock", "xsnoop", "snmpguess", "snmpgetattack",
    "httptunnel", "sendmail", "named",
}
_U2R = {
    "buffer_overflow", "loadmodule", "rootkit", "perl", "sqlattack", "xterm", "ps",
}


def label_to_class(label: str) -> int:
    if label == "normal":
        return 0
    if label in _DOS:
        return 1
    if label in _PROBE:
        return 2
    if label in _R2L:
        return 3
    if label in _U2R:
        return 4
    raise ValueError(f"étiquette inconnue: {label}")
