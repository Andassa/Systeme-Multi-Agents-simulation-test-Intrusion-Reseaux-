/**
 * Table d'encodage NSL-KDD - GENEREE depuis ml/artifacts/parametres_encodage.json
 *
 * NE PAS MODIFIER. Toute retouche serait perdue a la regeneration, et surtout
 * ferait diverger la simulation du modele entraine.
 *
 * Pourquoi ce fichier est genere et non ecrit a la main
 * -----------------------------------------------------
 * L'encodage (vocabulaires one-hot, bornes de normalisation) n'est pas une
 * decision de conception : c'est une DONNEE produite par l'apprentissage, sur
 * le TRAIN uniquement. La saisir a la main introduirait un risque de
 * divergence silencieuse entre ce que la foret a appris et ce que la
 * simulation lui presente - l'erreur la plus couteuse possible, puisqu'elle
 * degraderait les performances sans produire la moindre erreur d'execution.
 *
 * Regle appliquee a l'Etape 6 : est genere tout ce qui est derivable d'un
 * artefact existant ; reste en zone protegee ce qui encode une decision.
 *
 * 38 variables numeriques + 84 indicatrices = 122 composantes
 * Genere le : 2026-07-20 21:36
 */
model encodage_nslkdd

global {

    // Indices de racine des 20 arbres dans foret_table.csv
    list<int> RACINES_FORET <- [0,441,942,1371,2002,2429,3004,3565,4080,4639,5098,5573,6052,6575,7084,7651,8134,8683,9248,9739];

    // Bornes min/max etablies sur le TRAIN uniquement (les memes que
    // ml/preprocessing.py). Le test est ecrete a [0,1] apres application.
    list<float> BORNES_MIN <- [
        0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,
        0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,
        0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,
        0.000000,0.000000,0.000000,0.000000,0.000000
        ];
    list<float> BORNES_MAX <- [
        42908.000000,1379963888.000000,1309937401.000000,1.000000,3.000000,3.000000,77.000000,5.000000,
        1.000000,7479.000000,1.000000,2.000000,7468.000000,43.000000,2.000000,9.000000,0.000000,1.000000,
        1.000000,511.000000,511.000000,1.000000,1.000000,1.000000,1.000000,1.000000,1.000000,1.000000,
        255.000000,255.000000,1.000000,1.000000,1.000000,1.000000,1.000000,1.000000,1.000000,1.000000
        ];

    // Colonnes brutes numeriques, dans l'ordre du fichier NSL-KDD
    list<int> COLONNES_NUM <- [
        0,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,
        38,39,40
        ];

    // Vocabulaires one-hot : modalite -> indice de la composante.
    // Une modalite absente du vocabulaire laisse son bloc entierement nul -
    // c'est le comportement specifie en ADR-02 pour les modalites inconnues
    // du test, et il est mesure : 84 indicatrices au total.
    map<string, int> VOC_PROTOCOL_TYPE <- map(['icmp'::38,'tcp'::39,'udp'::40]);
    map<string, int> VOC_SERVICE <- map([
        'IRC'::41,'X11'::42,'Z39_50'::43,'aol'::44,'auth'::45,'bgp'::46,'courier'::47,'csnet_ns'::48,
        'ctf'::49,'daytime'::50,'discard'::51,'domain'::52,'domain_u'::53,'echo'::54,'eco_i'::55,
        'ecr_i'::56,'efs'::57,'exec'::58,'finger'::59,'ftp'::60,'ftp_data'::61,'gopher'::62,'harvest'::63,
        'hostnames'::64,'http'::65,'http_2784'::66,'http_443'::67,'http_8001'::68,'imap4'::69,
        'iso_tsap'::70,'klogin'::71,'kshell'::72,'ldap'::73,'link'::74,'login'::75,'mtp'::76,'name'::77,
        'netbios_dgm'::78,'netbios_ns'::79,'netbios_ssn'::80,'netstat'::81,'nnsp'::82,'nntp'::83,
        'ntp_u'::84,'other'::85,'pm_dump'::86,'pop_2'::87,'pop_3'::88,'printer'::89,'private'::90,
        'red_i'::91,'remote_job'::92,'rje'::93,'shell'::94,'smtp'::95,'sql_net'::96,'ssh'::97,'sunrpc'::98,
        'supdup'::99,'systat'::100,'telnet'::101,'tftp_u'::102,'tim_i'::103,'time'::104,'urh_i'::105,
        'urp_i'::106,'uucp'::107,'uucp_path'::108,'vmnet'::109,'whois'::110
        ]);
    map<string, int> VOC_FLAG <- map([
        'OTH'::111,'REJ'::112,'RSTO'::113,'RSTOS0'::114,'RSTR'::115,'S0'::116,'S1'::117,'S2'::118,'S3'::119,
        'SF'::120,'SH'::121
        ]);

    // Index nomme des 122 composantes du vecteur encode.
    // Permet d'ecrire les signatures RM1-RM11 avec les noms de variables du
    // CIM (`IDX['count']`, `IDX['flag=S0']`) plutot qu'avec des indices
    // numeriques, qu'aucun relecteur ne pourrait verifier.
    map<string, int> IDX <- map([
        'duration'::0,'src_bytes'::1,'dst_bytes'::2,'land'::3,'wrong_fragment'::4,'urgent'::5,'hot'::6,
        'num_failed_logins'::7,'logged_in'::8,'num_compromised'::9,'root_shell'::10,'su_attempted'::11,
        'num_root'::12,'num_file_creations'::13,'num_shells'::14,'num_access_files'::15,
        'num_outbound_cmds'::16,'is_host_login'::17,'is_guest_login'::18,'count'::19,'srv_count'::20,
        'serror_rate'::21,'srv_serror_rate'::22,'rerror_rate'::23,'srv_rerror_rate'::24,'same_srv_rate'::25,
        'diff_srv_rate'::26,'srv_diff_host_rate'::27,'dst_host_count'::28,'dst_host_srv_count'::29,
        'dst_host_same_srv_rate'::30,'dst_host_diff_srv_rate'::31,'dst_host_same_src_port_rate'::32,
        'dst_host_srv_diff_host_rate'::33,'dst_host_serror_rate'::34,'dst_host_srv_serror_rate'::35,
        'dst_host_rerror_rate'::36,'dst_host_srv_rerror_rate'::37,'protocol_type=icmp'::38,
        'protocol_type=tcp'::39,'protocol_type=udp'::40,'service=IRC'::41,'service=X11'::42,
        'service=Z39_50'::43,'service=aol'::44,'service=auth'::45,'service=bgp'::46,'service=courier'::47,
        'service=csnet_ns'::48,'service=ctf'::49,'service=daytime'::50,'service=discard'::51,
        'service=domain'::52,'service=domain_u'::53,'service=echo'::54,'service=eco_i'::55,
        'service=ecr_i'::56,'service=efs'::57,'service=exec'::58,'service=finger'::59,'service=ftp'::60,
        'service=ftp_data'::61,'service=gopher'::62,'service=harvest'::63,'service=hostnames'::64,
        'service=http'::65,'service=http_2784'::66,'service=http_443'::67,'service=http_8001'::68,
        'service=imap4'::69,'service=iso_tsap'::70,'service=klogin'::71,'service=kshell'::72,
        'service=ldap'::73,'service=link'::74,'service=login'::75,'service=mtp'::76,'service=name'::77,
        'service=netbios_dgm'::78,'service=netbios_ns'::79,'service=netbios_ssn'::80,'service=netstat'::81,
        'service=nnsp'::82,'service=nntp'::83,'service=ntp_u'::84,'service=other'::85,'service=pm_dump'::86,
        'service=pop_2'::87,'service=pop_3'::88,'service=printer'::89,'service=private'::90,
        'service=red_i'::91,'service=remote_job'::92,'service=rje'::93,'service=shell'::94,
        'service=smtp'::95,'service=sql_net'::96,'service=ssh'::97,'service=sunrpc'::98,
        'service=supdup'::99,'service=systat'::100,'service=telnet'::101,'service=tftp_u'::102,
        'service=tim_i'::103,'service=time'::104,'service=urh_i'::105,'service=urp_i'::106,
        'service=uucp'::107,'service=uucp_path'::108,'service=vmnet'::109,'service=whois'::110,
        'flag=OTH'::111,'flag=REJ'::112,'flag=RSTO'::113,'flag=RSTOS0'::114,'flag=RSTR'::115,'flag=S0'::116,
        'flag=S1'::117,'flag=S2'::118,'flag=S3'::119,'flag=SF'::120,'flag=SH'::121
        ]);

    /**
     * Valeur BRUTE d'une composante numerique, reconstituee depuis le vecteur
     * normalise.
     *
     * Necessaire parce que les signatures RM1-RM11 du CIM sont enoncees en
     * unites reelles (" count >= 100 ", " src_bytes > 1000 ") alors que
     * l'AgentReglesDetection recoit le vecteur normalise. Convertir les seuils
     * plutot que les valeurs aurait donne un code illisible et inverifiable
     * face au CIM.
     *
     * RESERVE : le test a ete ecrete a [0,1]. Une valeur superieure au maximum
     * du train est donc reconstituee a ce maximum, pas a sa valeur d'origine.
     * Sans effet sur RM1-RM11, dont les seuils sont tous tres inferieurs aux
     * maxima - mais toute signature future a seuil eleve devrait le savoir.
     */
    float valeur_brute (list<float> v, int j) {
        return v[j] * (BORNES_MAX[j] - BORNES_MIN[j]) + BORNES_MIN[j];
    }

    /**
     * Encode une ligne brute NSL-KDD (41 champs) en vecteur de 122 flottants.
     *
     * Compte localement les modalites jamais vues a l'apprentissage
     * (indicateur de deplacement de distribution du jeu de test).
     */
    list<float> encoder_connexion (list brut) {
        list<float> v <- list_with(122, 0.0);
        int nb_modalites_inconnues <- 0;

        // --- variables numeriques, normalisees min-max puis ecretees --------
        int j <- 0;
        loop c over: COLONNES_NUM {
            float x <- float(brut[c]);
            float etendue <- BORNES_MAX[j] - BORNES_MIN[j];
            float xn <- (etendue = 0.0) ? 0.0 : (x - BORNES_MIN[j]) / etendue;
            v[j] <- min(1.0, max(0.0, xn));
            j <- j + 1;
        }

        // --- variables categorielles, one-hot -------------------------------
        string m_protocol_type <- string(brut[1]);
        if (VOC_PROTOCOL_TYPE contains_key m_protocol_type) {
            v[int(VOC_PROTOCOL_TYPE[m_protocol_type])] <- 1.0;
        } else {
            nb_modalites_inconnues <- nb_modalites_inconnues + 1;
        }
        string m_service <- string(brut[2]);
        if (VOC_SERVICE contains_key m_service) {
            v[int(VOC_SERVICE[m_service])] <- 1.0;
        } else {
            nb_modalites_inconnues <- nb_modalites_inconnues + 1;
        }
        string m_flag <- string(brut[3]);
        if (VOC_FLAG contains_key m_flag) {
            v[int(VOC_FLAG[m_flag])] <- 1.0;
        } else {
            nb_modalites_inconnues <- nb_modalites_inconnues + 1;
        }

        return v;
    }

    /**
     * Classe reelle d'une ligne brute, lue depuis l'etiquette NSL-KDD.
     * ENF4 : cette action n'est appelee que par l'AgentJournalisation.
     */
    int classe_reelle (list brut) {
        string etiquette <- string(brut[41]);
        if ([
        'apache2','back','land','mailbomb','neptune','pod','processtable','smurf','teardrop','udpstorm',
        'worm'
        ] contains etiquette) { return 1; }
        if (['ipsweep','mscan','nmap','portsweep','saint','satan'] contains etiquette) { return 2; }
        if ([
        'ftp_write','guess_passwd','httptunnel','imap','multihop','named','phf','sendmail','snmpgetattack',
        'snmpguess','spy','warezclient','warezmaster','xlock','xsnoop'
        ] contains etiquette) { return 3; }
        if (['buffer_overflow','loadmodule','perl','ps','rootkit','sqlattack','xterm'] contains etiquette) { return 4; }
        return 0;   // NORMAL
    }
}
