-- Price changes from the daily API snapshots, cleaned.
-- One row = one price change at one station for one fuel type.
-- Each snapshot repeats prices that haven't changed, so identical rows are
-- grouped into one, matching the history files' "one row per change" format.

with source as (

    select * from {{ source('raw', 'api_prices') }}

),

changes as (

    -- Same station + fuel + price + update time = the same price change
    select
        trim(stationcode)        as station_code,
        upper(trim(fueltype))    as fuel_code,
        price                    as price_cpl,
        lastupdated              as price_updated_at_utc,
        min(snapshot_date)       as first_seen_snapshot,   -- first day the price appeared
        max(snapshot_date)       as last_seen_snapshot     -- last day it was still current
    from source
    group by station_code, fuel_code, price_cpl, price_updated_at_utc

),

with_dates as (

    select
        *,
        -- The API uses UTC; convert to Sydney time to match the history files
        datetime(price_updated_at_utc, 'Australia/Sydney')   as price_updated_at,
        date(price_updated_at_utc, 'Australia/Sydney')       as price_date,
        -- Days between the price's last update and the last snapshot showing it
        date_diff(last_seen_snapshot,
                  date(price_updated_at_utc, 'Australia/Sydney'), day) as price_age_days
    from changes

),

final as (

    select
        station_code,
        fuel_code,
        price_cpl,
        price_updated_at,
        price_updated_at_utc,
        price_date,
        first_seen_snapshot,
        last_seen_snapshot,
        price_age_days,

        -- Flags (rows are kept, never deleted)
        last_seen_snapshot = (select max(snapshot_date) from source) as is_current,  -- in the latest snapshot
        price_age_days > 7                                         as is_stale,    -- not updated for over 7 days
        fuel_code in ('E10', 'U91', 'P95', 'P98', 'DL', 'PDL')
            and price_cpl < 100                                    as is_outlier,
        fuel_code != 'EV'                                          as is_fuel      -- EV prices are almost all 0
    from with_dates

)

select * from final
