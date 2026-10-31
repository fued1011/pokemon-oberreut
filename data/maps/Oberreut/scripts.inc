Oberreut_MapScripts::
	.byte 0

Oberreut_EventScript_Sign::
	msgbox Oberreut_Text_Sign, MSGBOX_SIGN
	end

Oberreut_EventScript_Resident::
	msgbox Oberreut_Text_Resident, MSGBOX_NPC
	end

Oberreut_Text_Sign:
	.string "OBERREUT / JULIUS-LEBER-PLATZ\n"
	.string "GIS-Ausschnitt: 2 m je Feld.$"

Oberreut_Text_Resident:
	.string "Willkommen in OBERREUT!\p"
	.string "Am JULIUS-LEBER-PLATZ\n"
	.string "trifft sich das Viertel.$"
