/**
 * IDS multi-agents NSL-KDD — modèle GAMA (fichier unique).
 * Zones métier : @user-begin / @user-end
 *
 * Note GAMA 2025 : les imports de sous-modeles ne partagent pas le global
 * ni les types parent — d'ou ce monolithe (comportement inchange).
 */
model ids_sma

import "generated/encodage.gaml"
import "generated/foret_demo.gaml"

global {
    string PROTOCOLE_IDS <- 'no-protocol';
    list<string> CLASSES <- ['NORMAL', 'DOS', 'PROBE', 'R2L', 'U2R'];
    int NB_CLASSES <- 5;
    int NB_FEATURES <- 122;

    float poids_ia <- 0.35;
    float lambda_fp <- 0.0;
    int delai_garde <- 3;
    float seuil_alerte <- 0.5;
    int debit_capture <- 10;
    int capacite_file <- 200;
    bool verbose_alertes <- false;
    int limite_connexions <- 0;
    float taux_panne <- 0.0;
    float taux_reprise <- 0.20;
    float alpha_menace <- 0.99;
    float beta_menace <- 0.05;
    float niveau_menace <- 0.0;

    list<int> matrice_confusion <- list_with(25, 0);
    int nb_decisions <- 0;
    int nb_degradees <- 0;
    int nb_abandons <- 0;
    int nb_rejets_file <- 0;
    float exactitude_courante <- 0.0;
    float rappel_courant <- 0.0;
    float taux_fp_courant <- 0.0;

    file fichier_foret <- csv_file('generated/foret_table.csv', ',', true);
    matrix table_foret <- matrix(fichier_foret);
    list<int> racines_foret <- [];
    file fichier_donnees <- csv_file('data/KDDTest+.txt', ',', false);
    matrix donnees_nslkdd <- matrix(fichier_donnees);
    geometry shape <- rectangle(100, 80);

    list lire_connexion (int idc) {
        return list(donnees_nslkdd row_at idc);
    }

    int charge_decision {
        AgentDecision d <- first(AgentDecision);
        return length(d.file_idc) + ((d.etatDecision = 'INACTIF') ? 0 : 1);
    }

    action enregistrer_prediction (int reelle, int predite) {
        int cellule <- NB_CLASSES * reelle + predite;
        matrice_confusion[cellule] <- matrice_confusion[cellule] + 1;
        int total <- sum(matrice_confusion);
        int bons <- 0;
        loop k from: 0 to: NB_CLASSES - 1 {
            bons <- bons + matrice_confusion[NB_CLASSES * k + k];
        }
        exactitude_courante <- (total = 0) ? 0.0 : bons / float(total);

        int vp <- 0; int fn <- 0; int fp <- 0; int vn <- 0;
        loop r from: 0 to: NB_CLASSES - 1 {
            loop q from: 0 to: NB_CLASSES - 1 {
                int n <- matrice_confusion[NB_CLASSES * r + q];
                if (r = 0 and q = 0) { vn <- vn + n; }
                if (r = 0 and q > 0) { fp <- fp + n; }
                if (r > 0 and q = 0) { fn <- fn + n; }
                if (r > 0 and q > 0) { vp <- vp + n; }
            }
        }
        rappel_courant <- (vp + fn = 0) ? 0.0 : vp / float(vp + fn);
        taux_fp_courant <- (fp + vn = 0) ? 0.0 : fp / float(fp + vn);
    }

    init {
        racines_foret <- RACINES_FORET;
        create AgentCapture { location <- {12, 40}; libelle <- 'capture n=0'; }
        create AgentExtraction { location <- {28, 40}; libelle <- 'extraction n=0'; }
        create AgentReglesDetection { location <- {50, 22}; libelle <- 'regles abs=0'; }
        create AgentIADetection { location <- {50, 58}; libelle <- 'ia ACTIF n=0'; }
        create AgentDecision { location <- {68, 40}; libelle <- 'decision INACTIF q=0'; }
        create AgentAlertes { location <- {88, 22}; libelle <- 'alertes n=0'; }
        create AgentJournalisation { location <- {88, 58}; libelle <- 'journal n=0'; }
        write 'IDS-SMA pret - ' + string(donnees_nslkdd.rows) + ' connexions, cible exactitude ~0.810';
    }
}

species AgentVue skills: [fipa] {
    string identifiant <- '';
    string libelle <- '';
    rgb couleur <- rgb(127, 127, 127);
    float rayon <- 4.0;

    aspect pipeline {
        draw circle(rayon) color: couleur;
        draw libelle at: location + {0, 6} color: #black font: font('Arial', 10, #plain);
    }
}

species AgentCapture parent: AgentVue {
    string identifiant <- 'capture';
    rgb couleur <- rgb(70, 130, 180);
    int position <- 0;
    int nb_lues <- 0;

    reflex lire_flux when: position < donnees_nslkdd.rows and (limite_connexions = 0 or position < limite_connexions) and world.charge_decision() < capacite_file {
        loop i over: range(0, debit_capture - 1) {
            if (position < donnees_nslkdd.rows and (limite_connexions = 0 or position < limite_connexions) and world.charge_decision() < capacite_file) {
                int idc <- position;
                position <- position + 1;
                nb_lues <- nb_lues + 1;
                libelle <- identifiant + ' n=' + nb_lues;
                do start_conversation to: list(AgentExtraction) protocol: PROTOCOLE_IDS
                    performative: 'request' contents: ['P1', idc];
            }
        }
    }

    reflex traiter_echecs when: !empty(failures) {
        loop m over: copy(failures) {
            write '[capture] echec : ' + string(list(m.contents));
            do end_conversation message: m contents: ['fin'];
        }
    }

    reflex cloturer_p1 when: !empty(informs) {
        loop m over: copy(informs) {
            do end_conversation message: m contents: ['fin'];
        }
    }
}

species AgentExtraction parent: AgentVue {
    string identifiant <- 'extraction';
    rgb couleur <- rgb(44, 160, 44);
    map vocabulaires <- map([]);
    list<float> bornes_min <- [];
    list<float> bornes_max <- [];
    int nb_traitees <- 0;
    int nb_modalites_inconnues <- 0;

    reflex traiter_requetes when: !empty(requests) {
        loop m over: copy(requests) {
            list c <- list(m.contents);
            int idc <- int(c[1]);
            list brut <- world.lire_connexion(idc);
            list<float> v <- world.encoder_connexion(brut);
            nb_traitees <- nb_traitees + 1;
            libelle <- identifiant + ' n=' + nb_traitees;
            do inform message: m contents: ['P1', idc, ['v'::v]];
            do start_conversation to: list(AgentDecision) protocol: PROTOCOLE_IDS
                performative: 'inform' contents: ['P2', idc, ['v'::v]];
        }
    }
}

species AgentReglesDetection parent: AgentVue {
    string identifiant <- 'regles';
    rgb couleur <- rgb(255, 127, 14);
    int nb_regles <- 11;
    int nb_declenchements <- 0;
    int nb_abstentions <- 0;

    list<float> evaluer_signatures (list<float> v) {
        list<float> p <- list_with(NB_CLASSES, 1.0 / NB_CLASSES);
        bool declenchee <- false;
        // @user-begin(signatures_rm1_rm11)
        float meilleure <- 0.0;
        int classe_retenue <- 0;

        if (world.valeur_brute(v, int(IDX['serror_rate'])) > 0.8 and world.valeur_brute(v, int(IDX['count'])) >= 100 and 0.999 > meilleure) {
            meilleure <- 0.999; classe_retenue <- 1;
        }
        if (float(v[int(IDX['protocol_type=icmp'])]) = 1.0 and world.valeur_brute(v, int(IDX['src_bytes'])) > 1000 and 1.000 > meilleure) {
            meilleure <- 1.000; classe_retenue <- 1;
        }
        if (float(v[int(IDX['flag=S0'])]) = 1.0 and world.valeur_brute(v, int(IDX['same_srv_rate'])) > 0.9 and 0.575 > meilleure) {
            meilleure <- 0.575; classe_retenue <- 1;
        }
        if (world.valeur_brute(v, int(IDX['land'])) = 1 and 0.720 > meilleure) {
            meilleure <- 0.720; classe_retenue <- 1;
        }
        if (world.valeur_brute(v, int(IDX['diff_srv_rate'])) > 0.7 and 0.684 > meilleure) {
            meilleure <- 0.684; classe_retenue <- 2;
        }
        if (world.valeur_brute(v, int(IDX['rerror_rate'])) > 0.8 and world.valeur_brute(v, int(IDX['count'])) >= 50 and 0.233 > meilleure) {
            meilleure <- 0.233; classe_retenue <- 2;
        }
        if (world.valeur_brute(v, int(IDX['is_guest_login'])) = 1 and world.valeur_brute(v, int(IDX['hot'])) >= 1 and 0.265 > meilleure) {
            meilleure <- 0.265; classe_retenue <- 3;
        }
        if (world.valeur_brute(v, int(IDX['num_file_creations'])) >= 1 and world.valeur_brute(v, int(IDX['num_shells'])) >= 1 and 0.500 > meilleure) {
            meilleure <- 0.500; classe_retenue <- 4;
        }
        if (world.valeur_brute(v, int(IDX['num_failed_logins'])) >= 1 and world.valeur_brute(v, int(IDX['logged_in'])) = 0
            and (float(v[int(IDX['service=telnet'])]) = 1.0 or float(v[int(IDX['service=login'])]) = 1.0
                or float(v[int(IDX['service=ssh'])]) = 1.0 or float(v[int(IDX['service=ftp'])]) = 1.0
                or float(v[int(IDX['service=pop_3'])]) = 1.0 or float(v[int(IDX['service=imap4'])]) = 1.0)
            and 0.547 > meilleure) {
            meilleure <- 0.547; classe_retenue <- 3;
        }
        if (float(v[int(IDX['service=telnet'])]) = 1.0 and world.valeur_brute(v, int(IDX['num_failed_logins'])) >= 1 and 0.565 > meilleure) {
            meilleure <- 0.565; classe_retenue <- 3;
        }
        if (world.valeur_brute(v, int(IDX['root_shell'])) = 1 and world.valeur_brute(v, int(IDX['num_file_creations'])) >= 1 and 0.467 > meilleure) {
            meilleure <- 0.467; classe_retenue <- 4;
        }

        if (meilleure > 0.0) {
            declenchee <- true;
            loop k from: 0 to: NB_CLASSES - 1 {
                p[k] <- (1.0 - meilleure) / (NB_CLASSES - 1);
            }
            p[classe_retenue] <- meilleure;
        }
        // @user-end(signatures_rm1_rm11)
        if (declenchee) {
            nb_declenchements <- nb_declenchements + 1;
        } else {
            nb_abstentions <- nb_abstentions + 1;
        }
        libelle <- identifiant + ' abs=' + nb_abstentions;
        return p;
    }

    reflex repondre_consultations when: !empty(queries) {
        loop m over: copy(queries) {
            list c <- list(m.contents);
            int idc <- int(c[1]);
            list<float> p <- evaluer_signatures(list<float>(map(c[2])['v']));
            string nature <- (sum(p) - NB_CLASSES * min(p)) < 1e-9 ? 'ABSTENTION' : 'DETECTION';
            do inform message: m contents: ['P3', idc, 'regles', nature, p[0], p[1], p[2], p[3], p[4]];
        }
    }
}

species AgentIADetection parent: AgentVue control: fsm {
    string identifiant <- 'ia';
    rgb couleur <- rgb(148, 103, 189);
    int nb_predictions <- 0;
    int nb_refus_panne <- 0;

    list<float> predire (list<float> v) {
        list<float> acc <- list_with(NB_CLASSES, 0.0);
        loop __r over: racines_foret {
            int __n <- __r;
            loop while: (int(table_foret[0, __n]) >= 0) {
                __n <- (float(v[int(table_foret[0, __n])]) <= float(table_foret[1, __n]))
                    ? int(table_foret[2, __n]) : int(table_foret[3, __n]);
            }
            loop __k from: 0 to: NB_CLASSES - 1 {
                acc[__k] <- acc[__k] + float(table_foret[4 + __k, __n]);
            }
        }
        loop __k from: 0 to: NB_CLASSES - 1 {
            acc[__k] <- acc[__k] / length(racines_foret);
        }
        return acc;
    }

    state ACTIF initial: true {
        enter {
            couleur <- rgb(148, 103, 189);
        }
        loop m over: copy(queries) {
            list c <- list(m.contents);
            list<float> p <- predire(list<float>(map(c[2])['v']));
            nb_predictions <- nb_predictions + 1;
            libelle <- identifiant + ' ACTIF n=' + nb_predictions;
            do inform message: m contents: ['P3', int(c[1]), 'ia', 'DETECTION', p[0], p[1], p[2], p[3], p[4]];
        }
        transition to: EN_PANNE when: flip(taux_panne);
    }

    state EN_PANNE {
        enter {
            couleur <- rgb(214, 39, 40);
            libelle <- identifiant + ' EN_PANNE';
            write '[ia] panne au cycle ' + string(cycle);
        }
        loop m over: copy(queries) {
            nb_refus_panne <- nb_refus_panne + 1;
            do refuse message: m contents: ['P3', int(list(m.contents)[1]), 'agent en panne'];
        }
        transition to: ACTIF when: flip(taux_reprise);
    }
}

species AgentDecision parent: AgentVue control: weighted_tasks {
    string identifiant <- 'decision';
    rgb couleur <- rgb(31, 119, 180);
    float rayon <- 5.0;

    string etatDecision <- 'INACTIF';
    list<map> verdictsRecus <- [];
    int connexionCourante <- -1;
    list<float> vecteurCourant <- [];
    int cycleDebutConsultation <- -1;
    map decisionCourante <- map([]);
    int nb_refus_recus <- 0;
    bool requete_envoyee <- false;
    list<int> file_idc <- [];
    list<list<float>> file_vecteurs <- [];

    action demarrer_connexion (int idc, list<float> v) {
        connexionCourante <- idc;
        vecteurCourant <- v;
        verdictsRecus <- [];
        cycleDebutConsultation <- cycle;
        nb_refus_recus <- 0;
        requete_envoyee <- false;
        etatDecision <- 'CONSULTATION';
        libelle <- identifiant + ' CONSULTATION q=' + length(file_idc);
    }

    action prendre_suivant_en_file {
        if (etatDecision = 'INACTIF' and !empty(file_idc)) {
            int idc <- first(file_idc);
            list<float> v <- first(file_vecteurs);
            remove from: file_idc index: 0;
            remove from: file_vecteurs index: 0;
            do demarrer_connexion(idc: idc, v: v);
        }
    }

    action abandonner_cas {
        nb_abandons <- nb_abandons + 1;
        etatDecision <- 'INACTIF';
        libelle <- identifiant + ' INACTIF q=' + length(file_idc);
        do prendre_suivant_en_file;
    }

    bool toutes_abstentions {
        loop w over: verdictsRecus {
            if (string(w['nature']) != 'ABSTENTION') { return false; }
        }
        return true;
    }

    action trancher (bool degrade) {
        bool abs <- degrade
            ? (string(first(verdictsRecus)['nature']) = 'ABSTENTION')
            : toutes_abstentions();
        if (abs) {
            do abandonner_cas;
        } else {
            list<float> u <- utilite(degrade);
            decisionCourante <- [
                'classe'::CLASSES[index_of(u, max(u))],
                'confiance'::max(u),
                'degradee'::degrade
            ];
            etatDecision <- 'EMISSION';
            if (degrade) { nb_degradees <- nb_degradees + 1; }
            libelle <- identifiant + ' EMISSION q=' + length(file_idc);
        }
    }

    reflex reprendre_file when: etatDecision = 'INACTIF' and !empty(file_idc) {
        do prendre_suivant_en_file;
    }

    list<float> utilite (bool degrade) {
        list<float> u <- list_with(NB_CLASSES, 0.0);
        // @user-begin(calcul_utilite)
        list<float> c_ia <- list_with(NB_CLASSES, 0.0);
        list<float> c_rg <- list_with(NB_CLASSES, 0.0);
        bool a_ia <- false;
        bool a_rg <- false;
        loop w over: verdictsRecus {
            if (string(w['emetteur']) = 'ia') {
                c_ia <- list<float>(w['distribution']); a_ia <- true;
            } else {
                c_rg <- list<float>(w['distribution']); a_rg <- true;
            }
        }
        loop k from: 0 to: NB_CLASSES - 1 {
            float score <- degrade ? (a_ia ? c_ia[k] : c_rg[k])
                : (poids_ia * c_ia[k] + (1.0 - poids_ia) * c_rg[k]);
            float penalite <- (k = 0) ? 0.0 : lambda_fp * (1.0 - niveau_menace);
            u[k] <- score - penalite;
        }
        // @user-end(calcul_utilite)
        return u;
    }

    reflex recevoir_informs when: !empty(informs) {
        loop m over: copy(informs) {
            list c <- list(m.contents);
            string contrat <- string(c[0]);
            if (contrat = 'P2') {
                int idc <- int(c[1]);
                list<float> v <- list<float>(map(c[2])['v']);
                if (etatDecision = 'INACTIF' and empty(file_idc)) {
                    do demarrer_connexion(idc: idc, v: v);
                } else {
                    if (length(file_idc) < capacite_file) {
                        file_idc <- file_idc + [idc];
                        file_vecteurs <- file_vecteurs + [v];
                    } else {
                        nb_rejets_file <- nb_rejets_file + 1;
                    }
                }
                do end_conversation message: m contents: ['fin'];
            } else {
                if (contrat = 'P3') {
                    if (etatDecision = 'CONSULTATION' and length(c) >= 9) {
                        map verdict <- [
                            'emetteur'::string(c[2]),
                            'nature'::string(c[3]),
                            'distribution'::[float(c[4]), float(c[5]), float(c[6]), float(c[7]), float(c[8])]
                        ];
                        verdictsRecus <- verdictsRecus + [verdict];
                    }
                    do end_conversation message: m contents: ['fin'];
                }
            }
        }
    }

    reflex recevoir_refus when: !empty(refuses) {
        loop m over: copy(refuses) {
            nb_refus_recus <- nb_refus_recus + 1;
            do end_conversation message: m contents: ['fin'];
        }
    }

    task attendre weight: 0.1 { }

    task consulter weight: (etatDecision = 'CONSULTATION' and empty(verdictsRecus) and !requete_envoyee) ? 100.0 : 0.0 {
        do start_conversation to: list(AgentIADetection) + list(AgentReglesDetection)
            protocol: PROTOCOLE_IDS performative: 'query'
            contents: ['P3', connexionCourante, ['v'::vecteurCourant]];
        requete_envoyee <- true;
    }

    task fusionner weight: (etatDecision = 'CONSULTATION' and length(verdictsRecus) = 2) ? 90.0 : 0.0 {
        do trancher(degrade: false);
    }

    task emettre weight: (etatDecision = 'EMISSION') ? 95.0 : 0.0 {
        string classe_emise <- string(decisionCourante['classe']);
        float confiance_emise <- float(decisionCourante['confiance']);
        niveau_menace <- min(1.0, alpha_menace * niveau_menace
            + beta_menace * (classe_emise != 'NORMAL' ? 1.0 : 0.0));
        nb_decisions <- nb_decisions + 1;
        do start_conversation to: list(AgentAlertes) protocol: PROTOCOLE_IDS
            performative: 'inform' contents: ['P4', connexionCourante, classe_emise, confiance_emise];
        do start_conversation to: list(AgentJournalisation) protocol: PROTOCOLE_IDS
            performative: 'inform' contents: ['P5', connexionCourante, classe_emise, confiance_emise];
        if (nb_decisions mod 500 = 0) {
            write '[progres] ' + string(nb_decisions) + '/' + string(donnees_nslkdd.rows)
                + ' exactitude=' + string(exactitude_courante with_precision 3)
                + ' (cible ~0.810) rappel=' + string(rappel_courant with_precision 3);
        }
        etatDecision <- 'INACTIF';
        libelle <- identifiant + ' INACTIF q=' + length(file_idc);
        do prendre_suivant_en_file;
    }

    task fusionner_degrade weight: (etatDecision = 'CONSULTATION' and length(verdictsRecus) = 1
        and (nb_refus_recus > 0 or cycle - cycleDebutConsultation > delai_garde)) ? 80.0 : 0.0 {
        do trancher(degrade: true);
    }

    task abandonner weight: (etatDecision = 'CONSULTATION' and empty(verdictsRecus)
        and requete_envoyee and cycle - cycleDebutConsultation > delai_garde) ? 70.0 : 0.0 {
        do abandonner_cas;
    }
}

species AgentAlertes parent: AgentVue {
    string identifiant <- 'alertes';
    rgb couleur <- rgb(214, 39, 40);
    int nb_alertes <- 0;

    reflex traiter_decisions when: !empty(informs) {
        loop m over: copy(informs) {
            list c <- list(m.contents);
            string classe <- string(c[2]);
            float gravite <- float(c[3]) * (1.0 + niveau_menace) / 2.0;
            if (classe != 'NORMAL' and gravite >= seuil_alerte) {
                nb_alertes <- nb_alertes + 1;
                libelle <- identifiant + ' n=' + nb_alertes;
                if (verbose_alertes) {
                    write '[ALERTE] connexion ' + string(c[1]) + ' - ' + classe
                        + ' (gravite ' + string(gravite with_precision 3) + ')';
                }
            }
            do end_conversation message: m contents: ['fin'];
        }
    }
}

species AgentJournalisation parent: AgentVue {
    string identifiant <- 'journal';
    rgb couleur <- rgb(127, 127, 127);
    int nb_entrees <- 0;

    reflex journaliser when: !empty(informs) {
        loop m over: copy(informs) {
            list c <- list(m.contents);
            string classe_pred <- string(c[2]);
            nb_entrees <- nb_entrees + 1;
            libelle <- identifiant + ' n=' + nb_entrees;
            // @user-begin(mise_a_jour_matrice_confusion)
            int idc <- int(c[1]);
            if (idc >= 0 and idc < donnees_nslkdd.rows) {
                int reelle <- world.classe_reelle(world.lire_connexion(idc));
                int predite <- index_of(CLASSES, classe_pred);
                if (predite >= 0) {
                    ask world {
                        do enregistrer_prediction(reelle: reelle, predite: predite);
                    }
                }
            }
            // @user-end(mise_a_jour_matrice_confusion)
            do end_conversation message: m contents: ['fin'];
        }
    }
}

experiment ids_gui type: gui {
    parameter "Poids IA" var: poids_ia min: 0.0 max: 1.0 category: "Fusion";
    parameter "Penalite FP" var: lambda_fp min: 0.0 max: 1.0 category: "Fusion";
    parameter "Delai garde" var: delai_garde min: 1 max: 20 category: "Fusion";
    parameter "Seuil alerte" var: seuil_alerte min: 0.0 max: 1.0 category: "Alertes";
    parameter "Log alertes" var: verbose_alertes category: "Alertes";
    parameter "Debit capture" var: debit_capture min: 1 max: 100 category: "Capture";
    parameter "Capacite file" var: capacite_file min: 1 max: 500 category: "Capture";
    parameter "Limite (0=tout)" var: limite_connexions min: 0 max: 22544 category: "Capture";
    parameter "p_panne" var: taux_panne min: 0.0 max: 0.5 category: "Pannes";
    parameter "p_reprise" var: taux_reprise min: 0.0 max: 1.0 category: "Pannes";

    output {
        display "pipeline" type: 2d refresh: every(50#cycle) {
            species AgentCapture aspect: pipeline;
            species AgentExtraction aspect: pipeline;
            species AgentReglesDetection aspect: pipeline;
            species AgentIADetection aspect: pipeline;
            species AgentDecision aspect: pipeline;
            species AgentAlertes aspect: pipeline;
            species AgentJournalisation aspect: pipeline;
        }
        display "metriques" type: 2d refresh: every(50#cycle) {
            chart "Performance (0..1)" type: series {
                data "exactitude" value: exactitude_courante color: rgb(31, 119, 180);
                data "rappel" value: rappel_courant color: rgb(214, 39, 40);
                data "taux FP" value: taux_fp_courant color: rgb(127, 127, 127);
            }
        }
        display "menace_et_robustesse" type: 2d refresh: every(50#cycle) {
            chart "Menace mu" type: series {
                data "mu" value: niveau_menace color: rgb(255, 127, 14);
            }
            chart "Modes" type: histogram {
                data "nominales" value: nb_decisions - nb_degradees color: rgb(44, 160, 44);
                data "degradees" value: nb_degradees color: rgb(255, 127, 14);
                data "abandons" value: nb_abandons color: rgb(214, 39, 40);
            }
        }
        monitor "1. lues" value: first(AgentCapture).nb_lues;
        monitor "2. encodees" value: first(AgentExtraction).nb_traitees;
        monitor "3. decisions" value: nb_decisions;
        monitor "4. journal" value: first(AgentJournalisation).nb_entrees;
        monitor "5. alertes" value: first(AgentAlertes).nb_alertes;
        monitor "6. exactitude" value: (exactitude_courante with_precision 3);
        monitor "7. rappel" value: (rappel_courant with_precision 3);
        monitor "8. degradees" value: nb_degradees;
        monitor "9. file" value: world.charge_decision();
        monitor "10. ia" value: first(AgentIADetection).state;
    }
}
