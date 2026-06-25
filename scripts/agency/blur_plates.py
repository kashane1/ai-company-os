#!/usr/bin/env python3
"""Blur license plates (and other PII regions) into prospect demo-site photos.

Privacy/safety: gathered Google photos often show readable license plates. We bake
an irreversible blur+pixelate into the asset itself (NOT a CSS overlay) so plates
can't be recovered. Originals are backed up once to ``<assets>/_orig/`` so the op
is reproducible/reversible at source.

Regions are given as FRACTIONAL boxes (x0,y0,x1,y1 as fractions of width/height) so
they're resolution-independent — read them off any preview of the image.

One entry per site in SITES (keyed by place_id → assets dir + per-file boxes).
Edit/extend SITES below, then: python scripts/agency/blur_plates.py
"""
from __future__ import annotations
import shutil
from pathlib import Path
from PIL import Image, ImageFilter

SITES_ROOT = Path("/Users/kashane/dev/ai-company-os/state/prospects/sites")

# place_id -> { filename: [ (x0,y0,x1,y1) fractional boxes ] }
SITES: dict[str, dict[str, list[tuple[float, float, float, float]]]] = {
    # Integrity A/C Auto Climas (Phoenix) — shop-interior shot has a silver Nissan
    # Sentra with a readable Arizona plate (CPB9735) on the rear bumper.
    "ChIJFY_WoIMTK4cRhaOaKJkRNA4": {
        "shop-interior.jpg": [
            (0.255, 0.730, 0.460, 0.790),  # Sentra rear plate CPB9735 (lower-center)
        ],
    },
    # Confianza Insurance & Title Services (Austin) — storefront has cars in the lot.
    # No plate reads cleanly (sedan front is behind a hedge; van is side-on), but we
    # precautionarily obscure the front-of-vehicle zones so nothing recoverable ships.
    "ChIJzcJ8iPDLRIYR9QcXicSsWbs": {
        "storefront.jpg": [
            (0.000, 0.695, 0.090, 0.760),  # dark sedan front bumper (lower-left, behind hedge)
            (0.015, 0.610, 0.060, 0.665),  # van lower body / wheel zone (lower-left)
        ],
    },
    # Motor City Auto Repair (Dallas)
    "ChIJoa9yFfaYToYRTQDyXQvKrEw": {
        "hero.jpg": [
            (0.66, 0.78, 0.80, 0.855),    # Bentley rear plate (center-bottom)
            (0.835, 0.585, 0.945, 0.642), # Porsche plate (right)
        ],
        "storefront-wide.jpg": [
            (0.555, 0.80, 0.672, 0.862),  # Bentley rear plate
            (0.722, 0.680, 0.822, 0.732), # Porsche plate
        ],
        "lift-bay.jpg": [
            (0.888, 0.556, 0.974, 0.606), # Lexus rear plate (far right of frame)
        ],
        "sign.jpg": [
            (0.215, 0.696, 0.328, 0.742), # green sedan front plate
            (0.560, 0.690, 0.678, 0.737), # black SUV rear plate
        ],
    },
    # Alamo Fades & Shaves (San Antonio) — dusk storefront w/ two custom cars.
    # Burgundy Challenger carries a yellow personalized front plate ("BLACK MAMBA").
    "ChIJF0pml7b1XIYRwYnzSa6xsY0": {
        "night-cars.jpg": [
            (0.055, 0.698, 0.125, 0.732),  # Challenger front vanity plate (lower-left-center)
        ],
    },
    # Easy Tax Services LLC (Columbia Heights, MN) — storefront has a silver sedan
    # parked at the curb, seen through the glass entry door. No plate reads cleanly
    # (front 3/4, behind glass), but precaution-blur the visible vehicle body.
    "ChIJ7blWROk7s1IRnP95QBTJDUM": {
        "storefront.jpg": [
            (0.330, 0.838, 0.560, 0.935),  # silver sedan body (through entry glass, lower-center)
        ],
    },
    # Nail Envy and Spa (Baltimore) — two gallery photos include the salon's old
    # printed business card with STALE/incorrect branding (old name "Nails Envy &
    # Spa", old address 7836, old hours, a stock face) that contradicts the real
    # Google data. Bake an irreversible blur over the whole card so the demo never
    # ships the wrong contact info or the stock face.
    "ChIJY5uMG9wGyIkRK3I9t3T_yLo": {
        "art-animal.jpg": [
            (0.095, 0.620, 0.600, 0.875),  # business card, lower-center
        ],
        "art-navy.jpg": [
            (0.150, 0.455, 0.790, 0.750),  # business card, center-right
        ],
    },
    # Captain Auto (Fort Worth) — interior lift bay with a Range Rover + F-150 4x4.
    # Both already carry hand-drawn scribbles, but a sliver of the F-150 "TEXAS"
    # plate peeks above the scribble — bake a proper irreversible pixelate over both
    # plate regions so nothing recoverable ships.
    "ChIJOWKDKf56ToYRLB74UIYeU5A": {
        "work-lift.jpg": [
            (0.448, 0.478, 0.545, 0.560),  # red F-150 rear plate (center)
            (0.150, 0.792, 0.225, 0.852),  # black Range Rover front plate (lower-left)
        ],
    },
    # Cesar Luna Hair Salon (Chicago) — lobby shot looks out the front window onto the
    # street. Cars are parked side-on (no plate faces the camera), but precaution-blur
    # the dark-red sedan's rear quarter at the right edge so nothing recoverable ships.
    "ChIJU6HeTMrTD4gR_Dh77sTllY8": {
        "lounge.jpg": [
            (0.885, 0.175, 1.000, 0.330),  # dark red sedan rear quarter (far right, through window)
        ],
    },
    # Houston Mobile Mechanic & Diesel Repair (Houston)
    "ChIJcV_ilnrBQIYR62xFJZfYb-A": {
        "diesel-rig.jpg": [
            (0.335, 0.595, 0.485, 0.637),  # Peterbilt front plate (between OVER/SIZE)
        ],
        "night-work.jpg": [
            (0.165, 0.344, 0.250, 0.390),  # background grey Accord rear plate
            (0.010, 0.350, 0.085, 0.396),  # far-left dark blue sedan rear plate
        ],
        "fleet-work.jpg": [
            (0.035, 0.742, 0.155, 0.808),  # F-250 front bumper plate (lower-left)
        ],
    },
    # Detroit Tire Inc. (Detroit) — interior alignment-bay shot has two rear-facing
    # trucks parked at the back wall. No plate reads cleanly (the white SUV's rear is
    # half-occluded by a pole/welder; the black Ford's bumper has an empty plate
    # holder), but precaution-blur both rear-bumper zones so nothing recoverable ships.
    "ChIJn-tG9S_NJIgRxe4KmjnQ8pI": {
        "alignment-rack.jpg": [
            (0.690, 0.398, 0.775, 0.452),  # white SUV rear plate zone (center-right, behind pole)
            (0.820, 0.408, 0.930, 0.470),  # black Ford rear bumper/plate holder (right)
        ],
    },
    # Complete Diesel Repairz & Performance (San Antonio) — storefront hero with the
    # red GMC Denali. A white Ford Super Duty parked at far-left carries a readable
    # front plate; blur it. (Other trucks in this & the other photos are side-on or
    # plate-less; verified by high-res crops.)
    "ChIJQ9HEFSRcXIYRSQIYruFPfo4": {
        "hero-denali.jpg": [
            (0.070, 0.520, 0.112, 0.566),  # white F-Super-Duty front plate (far-left)
        ],
    },
    # LA PRIMERA Taxes & Insurance (Indianapolis) — storefront shots include parked
    # cars in the lot. No plate faces the camera in any chosen photo (the red SUV in
    # storefront.jpg is side-on; the red cars in storefront-wide.jpg / sign.jpg are
    # front-3/4 with no plate visible), verified by high-res crops. Precaution-blur the
    # prominent visible vehicle bodies so nothing recoverable ships.
    "ChIJgzE1xhNWa4gRryFLeDO0eeE": {
        "storefront-wide.jpg": [
            (0.000, 0.820, 0.150, 1.000),  # red car front corner (bottom-left)
        ],
        "sign.jpg": [
            (0.000, 0.855, 0.270, 1.000),  # red car front quarter (bottom-left corner)
        ],
    },
    # C B Hair & Nails (La Mesa) — two storefront shots each show a white Buick
    # parked in the lot with a readable California rear plate. Bake an irreversible
    # pixelate over each plate so nothing recoverable ships.
    "ChIJwz_Q-cRW2YARA6WMJ1LMHZ0": {
        "hero.jpg": [
            (0.748, 0.592, 0.818, 0.642),  # white Buick rear plate (center-right)
        ],
        "storefront.jpg": [
            (0.228, 0.512, 0.292, 0.560),  # white Buick rear plate (center-left)
        ],
    },
    # Benjamin's Barber Shop (Mesa, AZ) — hero glass reflects the strip-mall lot
    # (cars side/front-on, no plate reads cleanly, but precaution-blur the reflected
    # car band). One interior shot includes CUSTOMER faces (a dad + his child) and a
    # bystander filming on her phone reflected in the mirror — blur all non-staff
    # faces; the standing barber (Benjamin) is staff and stays sharp.
    "ChIJbzbluLSpK4cRyxvy49bdoag": {
        "hero.jpg": [
            (0.000, 0.575, 0.470, 0.74),   # parked-car reflection band (lower-left window)
            (0.470, 0.560, 0.640, 0.66),   # dark car reflected in the door glass (center)
        ],
        "chair-kids.jpg": [
            (0.255, 0.255, 0.405, 0.405),  # seated customer (dad) face
            (0.430, 0.285, 0.560, 0.425),  # child face
            (0.030, 0.150, 0.150, 0.270),  # bystander filming, reflected in mirror (far left)
            (0.410, 0.175, 0.490, 0.255),  # reflected seated customer face (mirror, center-left)
        ],
    },
    # Bluprint Nail Bar (Charlotte) — storefront shot taken from the parking ramp;
    # a parked car's roof/windshield sits in the bottom-left corner. No plate faces
    # the camera (we see the car from above, top-down), so nothing is readable, but
    # precaution-blur the visible vehicle body so nothing recoverable ships.
    "ChIJ4x_NrnwdVIgRt9FwYROrCRA": {
        "storefront.jpg": [
            (0.000, 0.870, 0.360, 1.000),  # parked car roof/windshield (bottom-left)
        ],
    },
    # Rounsavall Title Group, LLC (Louisville) — a real-estate/title company. The
    # "closing-day" property photo shows a red Subaru with a READABLE Kentucky rear
    # plate, plus a white Toyota whose front carries a dealer frame; bake an
    # irreversible pixelate over both. The monument-sign photo has cars parked in the
    # lot behind a hedge (no plate reads cleanly) — precaution-blur the visible car band.
    "ChIJQWSYKOB0aYgRoGybL_mms54": {
        "property-closing-day.jpg": [
            (0.840, 0.526, 0.885, 0.560),  # red Subaru rear plate (center-right)
            (0.423, 0.793, 0.503, 0.848),  # white Toyota front dealer frame (lower-center)
        ],
        "monument-sign.jpg": [
            (0.000, 0.465, 0.190, 0.535),  # parked-car band in the lot (left, behind hedge)
        ],
    },
    # Frank's Autobody & Repair (Camden, NJ) — daylight shot of a finished classic white
    # Rolls-Royce Silver Cloud rolling out of the bay; Frank stands beside it. The front
    # plate "941 CGA" reads cleanly at the lower-center of the grille. Bake an irreversible
    # pixelate over it. (Other chosen photos: plates masked/empty/side-on; verified by crop.)
    "ChIJWWL-JqfJxokRmw8Du6ukoo4": {
        "work-rolls.jpg": [
            (0.445, 0.682, 0.565, 0.742),  # Rolls-Royce front plate "941 CGA" (lower-center grille)
        ],
    },
    # Goddess Lashes (Tucson) — storefront shot shows the strip-mall lot through the glass.
    # A vehicle (SUV) sits behind the left window pane, lower-left of frame; no plate reads
    # cleanly through the tinted glass, but precaution-blur the visible vehicle body so
    # nothing recoverable ships. (storefront.jpg)
    "ChIJgbA9KqNv1oYR_zfBpRzxdJU": {
        "storefront.jpg": [
            (0.085, 0.855, 0.330, 1.000),  # SUV body through left window pane (lower-left)
        ],
    },
    # Gonzales Auto (Albuquerque) — storefront shot looks into the bay where a grey
    # Porsche Cayenne S is parked rear-to-camera with a READABLE Texas plate
    # ("1BD-2765") at the lower-center of the frame. Bake an irreversible pixelate over
    # it. (Other chosen photos: plates side-on / classics with no plate / staff portraits;
    # verified by high-res crops.)
    "ChIJ9SLW4DpzIocRupaeTpSsrw4": {
        "storefront.jpg": [
            (0.448, 0.815, 0.500, 0.868),  # Porsche Cayenne rear Texas plate (lower-center)
        ],
    },
    # HB Tires & Wheels (Denver) — tire shop. hero.jpg: silver Subaru Legacy being
    # serviced, readable Colorado rear plate. work-jeep.jpg: blue Jeep Liberty on a
    # jack with a readable Colorado front plate ("CMO V46"). storefront.jpg: red Subaru
    # Outback parked rear-to-camera in the bay with a small readable rear plate. Bake an
    # irreversible pixelate over each. (Boxes verified by 4-5x high-res crops.)
    "ChIJX0oyWgyBa4cRcjEas2AASY0": {
        "hero.jpg": [
            (0.790, 0.556, 0.852, 0.594),  # silver Subaru rear Colorado plate (center-right)
        ],
        "work-jeep.jpg": [
            (0.748, 0.620, 0.846, 0.692),  # blue Jeep front Colorado plate (center-right)
        ],
        "storefront.jpg": [
            (0.488, 0.578, 0.520, 0.595),  # red Outback rear plate (center, in the bay)
        ],
    },
    # Double Jays Collision, INC. (Detroit) — night hero of a gunmetal Dodge Charger
    # under the red "COLLISION" neon. The Charger carries a readable FRONT plate at the
    # lower-left of the frame; bake an irreversible pixelate over it. The background car
    # at far-right is front-3/4 with no plate facing the camera (verified by crop), so it
    # needs nothing.
    "ChIJH7Bl2HvMJIgRXLCvoQ5LZYw": {
        "hero.jpg": [
            (0.000, 0.600, 0.062, 0.672),  # Charger front plate (lower-left)
        ],
    },
    # Hair Forté (Sacramento) — daytime storefront has a dark car parked at the curb in
    # the bottom-left corner (side-on: front wheel + fender only, no plate faces the
    # camera; verified by high-res crop). Precaution-blur the visible vehicle body so
    # nothing recoverable ships. The window decals are graphic ads (no real faces).
    "ChIJM39o7VXamoARsOhHRpYV2Io": {
        "storefront-day.jpg": [
            (0.000, 0.855, 0.110, 1.000),  # dark car body (front wheel/fender, lower-left corner)
        ],
    },
    # Brandon Hill's Barber Shop (Jeffersonville, IN) — storefront crop (signage band).
    # The right entry window reflects the strip-mall lot: a parked car sits in the lower-
    # right glass (front-3/4, no plate reads cleanly, verified by high-res crop), but
    # precaution-blur the reflected vehicle body so nothing recoverable ships. The owner
    # (Brandon, staff) stays sharp; the children were cropped out of frame entirely.
    "ChIJIzqApFNyaYgRlcrQHsMK6KA": {
        "storefront.jpg": [
            (0.760, 0.760, 0.940, 0.960),  # reflected parked car in lower-right window glass
        ],
    },
    # Diamond Nails Spa (Dorchester/Boston) — a gallery shot (pink French + bling set)
    # is held up over the salon's own printed business card. The card exposes a partial
    # PHONE number ("…89") and the ZIP/address ("…02124", "11GR…") at the right and
    # lower-left of the card. Bake an irreversible pixelate over both text fragments so
    # no contact PII ships in the image. (No license plates / no third-party faces in any
    # Diamond Nails photo; all are hands/nails.)
    "ChIJ7bx6UXx744kRFREVAvUY6I0": {
        "work-french.jpg": [
            (0.495, 0.545, 0.660, 0.635),  # phone "…89" + zip "…02124" (right of card)
            (0.070, 0.595, 0.240, 0.665),  # "11GR…" street-address fragment (lower-left)
        ],
    },
    # D'Matrixx Salon By Irene (Milwaukee) — interior shot featuring the branded
    # red-script "D'Matrixx" floor mats (the asset we keep). The upper-right of the
    # frame has a row of stylists + clients at the styling chairs; their faces are
    # small/distant but identifiable. Bake an irreversible pixelate over the whole
    # people-band so no non-staff face ships. (No license plates in any D'Matrixx photo;
    # storefront lots are empty.)
    "ChIJBbYzj4kQBYgRqpnCso5EHaY": {
        "space-mats.jpg": [
            (0.485, 0.075, 0.930, 0.345),  # row of stylists + seated clients (upper-right band)
        ],
    },
    # Cuts Stop Barbershop (Malden, MA) — all interior/work photos, no vehicles/plates.
    # gallery-taper.jpg (curly-top taper fade) is a strong work shot but the client's
    # face reads in profile at center-right; pixelate the eye/cheek/mouth band so no
    # identifiable customer face ships. (Other chosen photos are no-face or face-obscured.)
    "ChIJP2Dgjx9z44kRTVvb1a2R7os": {
        "gallery-taper.jpg": [
            (0.520, 0.560, 0.840, 0.860),  # client face in profile (center-right, downturned)
        ],
    },
    # Laura's Hair Salon (Sunnyvale) — owner-operator salon. laura-working.jpg: Laura
    # (staff, stays sharp) stands at her station holding a service sheet; a male customer
    # in the background (center-left, against the world map) holds up a phone and his face
    # is identifiable. Bake an irreversible pixelate over the bystander's face. (The other
    # background person is back-to-camera, no face; verified by high-res crop. No license
    # plates in any kept Laura's photo — the neon-sign crop excludes the client-photo
    # collage entirely rather than blur dozens of faces.)
    "ChIJIXNtQDS3j4ARTeQtA2UDxJA": {
        "laura-working.jpg": [
            (0.188, 0.118, 0.288, 0.300),  # background male customer's face/head (center-left)
        ],
    },
    # Jrv Auto Repair (Haltom City / Fort Worth) — engine-rebuild shop. in-bay.jpg: white
    # Chevy Malibu front-end open in the bay with a READABLE Texas front plate ("DKC-26..",
    # partly behind a hoist arm, center). on-stands.jpg: blue Mini on jack stands; its front
    # plate is overexposed/blank (only "TEXAS" embossed reads) but precaution-pixelate it so
    # nothing recoverable ships. Boxes verified by 4x high-res crops.
    "ChIJE5WQG_h3ToYRMnAA9o_cBo4": {
        "in-bay.jpg": [
            (0.545, 0.405, 0.635, 0.470),  # white Chevy front Texas plate (center, behind hoist)
        ],
        "on-stands.jpg": [
            (0.355, 0.495, 0.560, 0.575),  # blue Mini front plate (lower-center, overexposed)
        ],
    },
    # Fine Nail (East Point / Atlanta) — three gallery work shots are held over the
    # salon's printed counter policy sign, which reads (reversed) "...accept...cards or
    # Discover", "...in CASH ONLY...", "we apologize for the inconvenience". That stale
    # cash-only messaging contradicts the real Google data (credit + debit accepted), so
    # bake an irreversible pixelate over each card-text band so the demo never ships
    # contradictory signage. work-snowflake.jpg has only blurry reflected neon (no PII)
    # but pixelate it for cleanliness. No license plates / no third-party faces in any
    # kept Fine Nail photo (work shots are hands/nails; interiors are empty of people).
    "ChIJ5eZM5EMd9YgRBkLvh3InSJw": {
        "work-peach.jpg": [
            (0.560, 0.330, 1.000, 0.730),  # reversed policy card (right of frame)
        ],
        "work-marble.jpg": [
            (0.000, 0.330, 0.470, 0.775),  # reversed policy card (lower-left)
        ],
        "work-snowflake.jpg": [
            (0.760, 0.330, 1.000, 0.690),  # reflected neon signage (right)
        ],
    },
    # Dapper Deluxe Club (Fresno) — barber shop, chair-cut.jpg is a work shot with a
    # seated CUSTOMER's identifiable face in profile (the standing barber is staff and
    # stays sharp). Bake an irreversible pixelate over the client face so no
    # identifiable customer ships. (No license plates in the kept set; the
    # storefront/parking shot was rejected; the second face-shot was dropped.)
    "ChIJfxOLvwhclIARqu3Hw4cReag": {
        "chair-cut.jpg": [
            (0.430, 0.285, 0.585, 0.470),  # seated client face (profile, center-right)
        ],
    },
    # Peraltas Auto Repair (Tucson) — work-classic.jpg shows a 1930s Chevy coupe project
    # on a trailer with a vintage "ARIZONA 70 … B60" plate readable at the lower-left;
    # bake an irreversible pixelate over it. work-lift.jpg has a lone worker standing in
    # the bay at the far lower-left whose face is small but identifiable; blur the face
    # region (privacy). Other photos: no plate faces the camera (verified by high-res crops).
    "ChIJxdpZmb561oYR-3zxRhs8rJA": {
        "work-classic.jpg": [
            (0.000, 0.525, 0.125, 0.610),  # vintage AZ plate "B60" (lower-left, on the coupe)
        ],
        "work-lift.jpg": [
            (0.000, 0.655, 0.060, 0.720),  # lone worker face (far lower-left of the bay)
        ],
    },
    # Flip N' Styles Barber (Milwaukee) — exterior-sign.jpg shows the round shop sign
    # over a snowy street; a grey Audi A4 parked at the curb carries a READABLE
    # Wisconsin rear plate ("AWH-2207") at the lower-center, and a dark sedan ahead of
    # it sits rear-3/4 (no plate reads cleanly, precaution-blur its rear zone). work-kid.jpg
    # is a strong cut shot but the seated CHILD's face is identifiable at center; bake an
    # irreversible pixelate over it. (Other kept photos: interior/work with no plate and
    # no third-party face — the stylist in work-cut.jpg is staff and the client is in
    # downturned profile; verified by high-res crops.)
    "ChIJF43TvBYaBYgRIuU_8ckLqas": {
        "exterior-sign.jpg": [
            (0.222, 0.812, 0.278, 0.848),  # Audi rear WI plate "AWH-2207" (lower-center)
            (0.430, 0.790, 0.490, 0.815),  # dark sedan rear zone ahead (precaution)
        ],
        "work-kid.jpg": [
            (0.485, 0.205, 0.560, 0.295),  # seated child's face (center)
        ],
    },
    # Rams #1 Automotive Services (El Paso) — the signboard shot has a gray Chrysler
    # 300 parked side-on in the foreground; its front faces off-frame to the left so
    # no plate reads, but precaution-blur the lower front-bumper zone so nothing
    # recoverable ships. The other gallery photos carry no readable plate (truck rear
    # tailgate has none, Sentra has an empty front plate bracket, Spark is side-on).
    "ChIJIVYe1qNc54YRibvqqpEQw44": {
        "sign.jpg": [
            (0.000, 0.870, 0.135, 0.990),  # Chrysler 300 front bumper/plate zone (lower-left)
        ],
    },
    # jasmine Hair salon & Barber Shop (Nashville) — dual salon+barber. hero.jpg
    # (interior, a cut in progress) has three identifiable faces: two staff barbers
    # (left w/ glasses, right) and the seated CUSTOMER (center). We pixelate ALL three
    # face regions so no identifiable person ships (privacy; staff consent unknown for a
    # demo). storefront.jpg ("Jasmine Salon" sign) has a door decal printing a phone
    # number ("615-831-1212") that CONTRADICTS the place-details number (615-429-9050);
    # bake an irreversible pixelate over the wrong number so no conflicting contact info
    # ships. (The black car at bottom-right is side-on with no readable plate; verified
    # by high-res crop. The window poster faces are printed salon-advert graphics.)
    "ChIJoR4SEr9vZIgRYpzNFr6jiqA": {
        "hero.jpg": [
            (0.515, 0.560, 0.575, 0.610),  # left barber face (glasses)
            (0.545, 0.595, 0.615, 0.640),  # seated customer face (center)
            (0.610, 0.585, 0.670, 0.630),  # right barber face
        ],
        "storefront.jpg": [
            (0.215, 0.498, 0.425, 0.540),  # door-decal phone "615-831-1212" (conflicts w/ place-details)
        ],
    },
    # J Klips (Minneapolis) — barbershop. work-fade.jpg (a box-fade line-up work shot)
    # looks out the front window; a blue Ford SUV parked outside carries a READABLE
    # Minnesota rear plate ("AVG 007") reflected/seen through the glass at the
    # center-right. Bake an irreversible pixelate over it. (Other kept photos are
    # interior/work with no readable plate; verified by high-res crops.)
    "ChIJLzyBIRko9ocRhyMW3-Q8WZg": {
        "work-fade.jpg": [
            (0.815, 0.555, 0.965, 0.640),  # blue Ford rear MN plate "AVG 007" (center-right, through glass)
        ],
    },
}


def obscure(img: Image.Image, box_frac: tuple[float, float, float, float]) -> None:
    w, h = img.size
    x0, y0, x1, y1 = box_frac
    px = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    region = img.crop(px)
    # pixelate: downscale hard then upscale (destroys characters), then soften
    small = region.resize((max(1, region.width // 18), max(1, region.height // 18)), Image.BILINEAR)
    pix = small.resize(region.size, Image.NEAREST)
    pix = pix.filter(ImageFilter.GaussianBlur(6))
    img.paste(pix, px[:2])


def main() -> None:
    for place_id, regions in SITES.items():
        assets = SITES_ROOT / place_id / "dist-v2" / "assets"
        backup = assets / "_orig"
        backup.mkdir(parents=True, exist_ok=True)
        print(f"# {place_id}")
        for name, boxes in regions.items():
            src = assets / name
            if not src.is_file():
                print(f"  ! missing {name}")
                continue
            bak = backup / name
            if not bak.is_file():
                shutil.copy2(src, bak)  # one-time backup of the pristine original
            img = Image.open(bak).convert("RGB")  # always start from the pristine copy
            for b in boxes:
                obscure(img, b)
            # high quality + no chroma subsampling so the re-encode is visually lossless
            # (only the plate region changes; the rest of the photo stays sharp)
            img.save(src, "JPEG", quality=95, subsampling=0, optimize=True)
            print(f"  ✓ {name}: blurred {len(boxes)} region(s)  ({img.width}x{img.height})")
    print("done.")


if __name__ == "__main__":
    main()
