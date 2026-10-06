/**
 * foretDemo - cible INLINE (ADR-03 bis)
 *
 * FICHIER GENERE depuis ../ml/artifacts/foret_export.json. Ne pas modifier.
 *
 * AVERTISSEMENT A NE PAS OMETTRE DANS LE MEMOIRE
 * ----------------------------------------------
 * Ce fichier n'est PAS une autre ecriture du classifieur de production.
 * C'est une foret REDUITE - 3 arbres de profondeur 4,
 * contre 20 arbres de profondeur 12 en production.
 * Ses predictions different, et ses performances sont inferieures.
 *
 * Sa raison d'etre est la lisibilite : 211 lignes qu'un lecteur peut
 * suivre, la ou la foret de production compte 10232 n?uds et ne
 * peut etre lue. Pretendre qu'il s'agit du meme modele sous deux formes se
 * verrait a la premiere question du jury.
 *
 * Genere le : 2026-07-20 21:36
 */
model foretdemo

global {

    /**
     * Classifieur lisible - cascade de tests explicites.
     *
     * Chaque branche porte en commentaire le nom de la variable NSL-KDD
     * testee, de sorte que la logique apprise soit lisible sans se referer
     * a la table d'encodage.
     */
    list predire_demo (list<float> v) {
        list<float> acc <- list_with(5, 0.0);

        // ---- arbre 0 ----
        // dst_host_srv_serror_rate
        if (v[35] <= 0.143750) {
            // service=telnet
            if (v[101] <= 0.000000) {
                // hot
                if (v[6] <= 0.000000) {
                    // dst_bytes
                    if (v[2] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0846; acc[1] <- acc[1] + 0.1221; acc[2] <- acc[2] + 0.4972; acc[3] <- acc[3] + 0.2758; acc[4] <- acc[4] + 0.0203;
                    } else {
                        acc[0] <- acc[0] + 0.8735; acc[1] <- acc[1] + 0.0002; acc[2] <- acc[2] + 0.0159; acc[3] <- acc[3] + 0.0263; acc[4] <- acc[4] + 0.0840;
                    }
                } else {
                    // service=ftp
                    if (v[60] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0298; acc[1] <- acc[1] + 0.1179; acc[2] <- acc[2] + 0.0048; acc[3] <- acc[3] + 0.3094; acc[4] <- acc[4] + 0.5382;
                    } else {
                        acc[0] <- acc[0] + 0.0329; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.8212; acc[4] <- acc[4] + 0.1459;
                    }
                }
            } else {
                // dst_host_srv_count
                if (v[29] <= 0.039216) {
                    // dst_host_rerror_rate
                    if (v[36] <= 0.380000) {
                        acc[0] <- acc[0] + 0.0073; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0020; acc[3] <- acc[3] + 0.0063; acc[4] <- acc[4] + 0.9844;
                    } else {
                        acc[0] <- acc[0] + 0.0795; acc[1] <- acc[1] + 0.2040; acc[2] <- acc[2] + 0.2680; acc[3] <- acc[3] + 0.4485; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // dst_host_srv_serror_rate
                    if (v[35] <= 0.000000) {
                        acc[0] <- acc[0] + 0.6697; acc[1] <- acc[1] + 0.2578; acc[2] <- acc[2] + 0.0725; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0427; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0094; acc[3] <- acc[3] + 0.9479; acc[4] <- acc[4] + 0.0000;
                    }
                }
            }
        } else {
            // srv_count
            if (v[20] <= 0.001957) {
                // flag=SH
                if (v[121] <= 0.000000) {
                    // rerror_rate
                    if (v[23] <= 0.000000) {
                        acc[0] <- acc[0] + 0.1122; acc[1] <- acc[1] + 0.7960; acc[2] <- acc[2] + 0.0199; acc[3] <- acc[3] + 0.0718; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0353; acc[1] <- acc[1] + 0.0190; acc[2] <- acc[2] + 0.9457; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 1.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                }
            } else {
                // rerror_rate
                if (v[23] <= 0.120000) {
                    // dst_host_count
                    if (v[28] <= 0.039216) {
                        acc[0] <- acc[0] + 0.0387; acc[1] <- acc[1] + 0.1630; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.7982; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0028; acc[1] <- acc[1] + 0.9972; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // num_failed_logins
                    if (v[7] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0029; acc[1] <- acc[1] + 0.0559; acc[2] <- acc[2] + 0.9411; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 1.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            }
        }
        // ---- arbre 1 ----
        // flag=S0
        if (v[116] <= 0.000000) {
            // dst_bytes
            if (v[2] <= 0.000000) {
                // srv_diff_host_rate
                if (v[27] <= 0.330000) {
                    // dst_host_same_srv_rate
                    if (v[30] <= 0.130000) {
                        acc[0] <- acc[0] + 0.0448; acc[1] <- acc[1] + 0.1982; acc[2] <- acc[2] + 0.6989; acc[3] <- acc[3] + 0.0100; acc[4] <- acc[4] + 0.0481;
                    } else {
                        acc[0] <- acc[0] + 0.1137; acc[1] <- acc[1] + 0.0788; acc[2] <- acc[2] + 0.1271; acc[3] <- acc[3] + 0.6376; acc[4] <- acc[4] + 0.0428;
                    }
                } else {
                    // rerror_rate
                    if (v[23] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0272; acc[1] <- acc[1] + 0.0070; acc[2] <- acc[2] + 0.9161; acc[3] <- acc[3] + 0.0497; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.9237; acc[1] <- acc[1] + 0.0041; acc[2] <- acc[2] + 0.0722; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            } else {
                // dst_host_diff_srv_rate
                if (v[31] <= 0.010000) {
                    // root_shell
                    if (v[10] <= 0.000000) {
                        acc[0] <- acc[0] + 0.5738; acc[1] <- acc[1] + 0.0187; acc[2] <- acc[2] + 0.0004; acc[3] <- acc[3] + 0.0843; acc[4] <- acc[4] + 0.3228;
                    } else {
                        acc[0] <- acc[0] + 0.0028; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0179; acc[4] <- acc[4] + 0.9793;
                    }
                } else {
                    // dst_host_diff_srv_rate
                    if (v[31] <= 0.050000) {
                        acc[0] <- acc[0] + 0.2419; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0029; acc[3] <- acc[3] + 0.6232; acc[4] <- acc[4] + 0.1320;
                    } else {
                        acc[0] <- acc[0] + 0.3899; acc[1] <- acc[1] + 0.0001; acc[2] <- acc[2] + 0.0823; acc[3] <- acc[3] + 0.0499; acc[4] <- acc[4] + 0.4778;
                    }
                }
            }
        } else {
            // dst_host_srv_diff_host_rate
            if (v[33] <= 0.000000) {
                // dst_host_rerror_rate
                if (v[36] <= 0.030000) {
                    // dst_host_serror_rate
                    if (v[34] <= 0.510000) {
                        acc[0] <- acc[0] + 0.3540; acc[1] <- acc[1] + 0.0425; acc[2] <- acc[2] + 0.6035; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0001; acc[1] <- acc[1] + 0.9999; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // hot
                    if (v[6] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0030; acc[1] <- acc[1] + 0.0240; acc[2] <- acc[2] + 0.9730; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 1.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            } else {
                // dst_host_same_srv_rate
                if (v[30] <= 0.510000) {
                    // dst_host_same_src_port_rate
                    if (v[32] <= 0.110000) {
                        acc[0] <- acc[0] + 0.0575; acc[1] <- acc[1] + 0.9425; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 1.0000; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    acc[0] <- acc[0] + 0.8777; acc[1] <- acc[1] + 0.1223; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                }
            }
        }
        // ---- arbre 2 ----
        // flag=S0
        if (v[116] <= 0.000000) {
            // logged_in
            if (v[8] <= 0.000000) {
                // dst_host_diff_srv_rate
                if (v[31] <= 0.120000) {
                    // service=eco_i
                    if (v[55] <= 0.000000) {
                        acc[0] <- acc[0] + 0.2931; acc[1] <- acc[1] + 0.2634; acc[2] <- acc[2] + 0.0978; acc[3] <- acc[3] + 0.1106; acc[4] <- acc[4] + 0.2351;
                    } else {
                        acc[0] <- acc[0] + 0.0205; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.9795; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // src_bytes
                    if (v[1] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0026; acc[1] <- acc[1] + 0.0008; acc[2] <- acc[2] + 0.9966; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.6851; acc[1] <- acc[1] + 0.2668; acc[2] <- acc[2] + 0.0481; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            } else {
                // service=http
                if (v[65] <= 0.000000) {
                    // srv_diff_host_rate
                    if (v[27] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0673; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0040; acc[3] <- acc[3] + 0.4183; acc[4] <- acc[4] + 0.5105;
                    } else {
                        acc[0] <- acc[0] + 0.7746; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0040; acc[3] <- acc[3] + 0.2213; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // src_bytes
                    if (v[1] <= 0.000002) {
                        acc[0] <- acc[0] + 0.9847; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 0.0002; acc[3] <- acc[3] + 0.0151; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0089; acc[1] <- acc[1] + 0.9911; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            }
        } else {
            // dst_host_diff_srv_rate
            if (v[31] <= 0.740000) {
                // serror_rate
                if (v[21] <= 0.500000) {
                    // dst_host_srv_count
                    if (v[29] <= 0.019608) {
                        acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.2024; acc[2] <- acc[2] + 0.7976; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.9867; acc[1] <- acc[1] + 0.0133; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                } else {
                    // service=link
                    if (v[74] <= 0.000000) {
                        acc[0] <- acc[0] + 0.0010; acc[1] <- acc[1] + 0.9950; acc[2] <- acc[2] + 0.0040; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    } else {
                        acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.9335; acc[2] <- acc[2] + 0.0665; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                    }
                }
            } else {
                // dst_host_rerror_rate
                if (v[36] <= 0.000000) {
                    acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 1.0000; acc[2] <- acc[2] + 0.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                } else {
                    acc[0] <- acc[0] + 0.0000; acc[1] <- acc[1] + 0.0000; acc[2] <- acc[2] + 1.0000; acc[3] <- acc[3] + 0.0000; acc[4] <- acc[4] + 0.0000;
                }
            }
        }

        loop __k from: 0 to: 5 - 1 {
            acc[__k] <- acc[__k] / 3;
        }
        return acc;
    }
}
