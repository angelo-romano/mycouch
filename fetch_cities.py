import csv
import simplejson
import sys
from strings import force_str, force_unicode
from mycouch.models import City, Country


def prepare_countries():
    countries = [
        ('ALB', 'Albania'),
        ('AND', 'Andorra'),
        ('AUT', 'Austria'),
        ('BEL', 'Belgium'),
        ('BGR', 'Bulgaria'),
        ('BIH', 'Bosnia and Herzegovina'),
        ('BLR', 'Belarus'),
        ('CHE', 'Switzerland'),
        ('CYP', 'Cyprus'),
        ('CZE', 'Czech Republic'),
        ('DEU', 'Germany'),
        ('DNK', 'Denmark'),
        ('ESP', 'Spain'),
        ('EST', 'Estonia'),
        ('FIN', 'Finland'),
        ('FRA', 'France'),
        ('FRO', 'Faroe Islands'),
        ('GBR', 'United Kingdom'),
        ('GIB', 'Gibraltar'),
        ('GRC', 'Greece'),
        ('GRL', 'Greenland'),
        ('HRV', 'Croatia'),
        ('HUN', 'Hungary'),
        #('IMN', 'Isle of Man'),
        ('IRL', 'Ireland'),
        ('ISL', 'Iceland'),
        ('ISR', 'Israel'),
        ('ITA', 'Italy'),
        ('LIE', 'Liechtenstein'),
        ('LTU', 'Lithuania'),
        ('LUX', 'Luxembourg'),
        ('LVA', 'Latvia'),
        ('MCO', 'Monaco'),
        ('MDA', 'Republic of Moldova'),
        ('MKD', 'Macedonia (FYROM)'),
        ('MLT', 'Malta'),
        ('MNE', 'Montenegro'),
        ('NLD', 'Netherlands'),
        ('NOR', 'Norway'),
        ('POL', 'Poland'),
        ('PRT', 'Portugal'),
        ('ROU', 'Romania'),
        ('RUS', 'Russian Federation'),
        ('SMR', 'San Marino'),
        ('SRB', 'Serbia'),
        ('SVK', 'Slovakia'),
        ('SVN', 'Slovenia'),
        ('SWE', 'Sweden'),
        ('TUR', 'Turkey'),
        ('UNK', 'Kosovo'),
        ('UKR', 'Ukraine'),
        ('VAT', 'Holy See (Vatican City)'),
    ]
    country_list = Country.query.all()
    if not country_list:
        for code, name in countries:
            country = Country(name=name, code=code)
            country.save(commit=True)
        country_list = Country.query.all()
    return dict((o.code, o.id) for o in country_list)


def parse_csv(csvfile):
    resp_one = []
    country_dict = prepare_countries()
    with open(csvfile, 'r') as fh:
        reader = csv.reader(fh)
        for line in reader:
            local_name, country_code, lat, lng, is_city, data = line
            is_city = (is_city == 'True')
            if not is_city or not local_name:
                continue
            data = simplejson.loads(data)
            name = None
            if 'name:en' in data:
                name = data.get('name:en')
            elif 'name' in data:
                name = data.get('name')
            if not name:
                name = local_name
            if data.get('place') in ('hamlet', 'village'):
                continue
            orig_municipality = data.get('is_in:municipality') or data.get('is_in:city')
            name = force_str(name)
            local_name = force_str(local_name)
            if orig_municipality:
                if ',' in orig_municipality:
                    orig_municipality = orig_municipality.split(',')[0]

                if ';' in orig_municipality:
                    orig_municipality = orig_municipality.split(';')[0]
                orig_municipality = force_str(orig_municipality)
                if (orig_municipality != name and orig_municipality != local_name):
                    continue
            resp_one.append((name, country_code, lat, lng, data, len(data.keys())))

        resp_one.sort(key=lambda k: (-k[-1], k[0]))
        for name, country_code, lat, lng, data, popularity in resp_one:
            if not data:
                data = {}
            city = City(name=force_unicode(name), coordinates=[lat, lng], rating=popularity,
                        additional_data=data,
                        country_id=country_dict[country_code])
            city.save(commit=True)


if __name__ == '__main__':
    parse_csv(sys.argv[1])
