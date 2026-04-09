import { Hotel, Flight, ToolResultSnapshot, HotelSearchResult, FlightSearchResult, TravelTipsResult, HotelDetailResult, RoomType } from '../types'
// hotel click enabled
interface Props {
  snapshot: ToolResultSnapshot
  onHotelClick?: (hotelCode: string, hotelName: string) => void
}

export function ToolResultCard({ snapshot, onHotelClick }: Props) {
  const { tool, result } = snapshot

  if (tool === 'search_hotels') {
    return <HotelCard data={result as HotelSearchResult} onHotelClick={onHotelClick} />
  }
  if (tool === 'search_flights') {
    return <FlightCard data={result as FlightSearchResult} />
  }
  if (tool === 'get_travel_tips') {
    return <TipsCard data={result as TravelTipsResult} />
  }
  if (tool === 'get_hotel_detail') {
    return <HotelDetailCard data={result as HotelDetailResult} />
  }
  return null
}

// ── 호텔 카드 ──────────────────────────────────
function HotelCard({ data, onHotelClick }: { data: HotelSearchResult; onHotelClick?: (hotelCode: string, hotelName: string) => void }) {
  if (data.status !== 'success' || !data.hotels?.length) return null
  return (
    <div className="tool-card hotel-result-card">
      <div className="tool-card-header">
        <span className="tool-icon">🏨</span>
        <span className="tool-title">
          {data.city} 호텔 검색결과
        </span>
        <span className="tool-meta">
          {data.check_in} ~ {data.check_out} · {data.guests}명
        </span>
      </div>
      {onHotelClick && (
        <div className="hotel-scroll-hint">
          <span className="scroll-hint-icon">←</span>
          <span>좌우로 스크롤하여 더 많은 호텔을 확인하세요</span>
          <span className="scroll-hint-icon">→</span>
        </div>
      )}
      <div className="hotel-scroll-container">
        <div className="hotel-scroll-track">
          {data.hotels!.map((h, i) => (
            <HotelItem key={i} hotel={h} onHotelClick={onHotelClick} index={i} />
          ))}
        </div>
      </div>
    </div>
  )
}

function HotelItem({ hotel, onHotelClick, index }: { hotel: Hotel; onHotelClick?: (hotelCode: string, hotelName: string) => void; index: number }) {
  const clickable = !!onHotelClick
  const gradients = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  ]
  const gradient = gradients[index % gradients.length]

  return (
    <div
      className={`hotel-card${clickable ? ' clickable' : ''}`}
      onClick={clickable ? () => onHotelClick(hotel.hotel_code, hotel.name) : undefined}
    >
      <div className="hotel-card-image">
        <div className="hotel-image-placeholder" style={{ background: gradient }}>
          <span className="hotel-emoji">🏨</span>
        </div>
        <div className="hotel-stars-badge">{'★'.repeat(hotel.stars)}</div>
        {clickable && <div className="hotel-hover-overlay">상세 보기 →</div>}
      </div>
      <div className="hotel-card-content">
        <div className="hotel-card-main">
          <h4 className="hotel-card-name">{hotel.name}</h4>
          <p className="hotel-card-area">{hotel.area}</p>
        </div>
        <div className="hotel-card-stats">
          <div className="hotel-stat-item">
            <span className="hotel-stat-icon">⭐</span>
            <span className="hotel-stat-value">{hotel.rating}</span>
          </div>
          <div className="hotel-stat-item">
            <span className="hotel-stat-icon">🎯</span>
            <span className="hotel-stat-value">{hotel.stars}성급</span>
          </div>
        </div>
        <div className="hotel-card-price">
          <span className="price-value">{hotel.price.toLocaleString()}</span>
          <span className="price-unit">원/박</span>
        </div>
      </div>
    </div>
  )
}

// ── 호텔 상세 카드 ─────────────────────────────
function HotelDetailCard({ data }: { data: HotelDetailResult }) {
  if (data.status !== 'success') return null
  return (
    <div className="tool-card hotel-detail-card">
      <div className="tool-card-header">
        <span className="tool-icon">🏨</span>
        <div className="hotel-detail-header-body">
          <span className="tool-title">{data.name}</span>
          <span className="hotel-detail-stars">{'★'.repeat(data.stars ?? 0)}{'☆'.repeat(5 - (data.stars ?? 0))}</span>
        </div>
        <span className="tool-meta">{data.city} · {data.area}</span>
      </div>

      <div className="hotel-detail-meta-row">
        <span className="hotel-detail-rating">⭐ {data.rating} / 5.0</span>
        <span className="hotel-detail-address">📍 {data.address}</span>
        <span className="hotel-detail-phone">📞 {data.phone}</span>
      </div>

      <div className="hotel-detail-description">{data.description}</div>

      {data.highlights && data.highlights.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">✨ 주요 특징</div>
          <div className="hotel-highlights">
            {data.highlights.map((h, i) => (
              <span key={i} className="hotel-highlight-tag">{h}</span>
            ))}
          </div>
        </div>
      )}

      {data.room_types && data.room_types.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">🛏️ 객실 타입</div>
          <div className="hotel-room-grid">
            {data.room_types.map((room, i) => (
              <RoomTypeItem key={i} room={room} />
            ))}
          </div>
        </div>
      )}

      {data.amenities && data.amenities.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">🎯 편의시설</div>
          <div className="hotel-amenities">
            {data.amenities.map((a, i) => (
              <span key={i} className="hotel-amenity-tag">{a}</span>
            ))}
          </div>
        </div>
      )}

      <div className="hotel-detail-policies">
        <div className="hotel-policy-item">
          <span className="hotel-policy-label">체크인</span>
          <span className="hotel-policy-value">{data.check_in_time}</span>
        </div>
        <div className="hotel-policy-divider" />
        <div className="hotel-policy-item">
          <span className="hotel-policy-label">체크아웃</span>
          <span className="hotel-policy-value">{data.check_out_time}</span>
        </div>
        <div className="hotel-policy-divider" />
        <div className="hotel-policy-item hotel-policy-cancel">
          <span className="hotel-policy-label">취소 정책</span>
          <span className="hotel-policy-value">{data.cancel_policy}</span>
        </div>
      </div>
    </div>
  )
}

function RoomTypeItem({ room }: { room: RoomType }) {
  return (
    <div className="hotel-room-item">
      <div className="hotel-room-type">{room.type}</div>
      <div className="hotel-room-meta">
        <span>{room.size}</span>
        <span>최대 {room.max_guests}명</span>
        <span>{room.bed}</span>
      </div>
      <div className="hotel-room-price">{room.price_per_night.toLocaleString()}원<small>/박</small></div>
    </div>
  )
}

// ── 항공 카드 ──────────────────────────────────
function FlightCard({ data }: { data: FlightSearchResult }) {
  if (data.status !== 'success') return null

  const isRoundTrip = data.trip_type === 'round_trip'
  const hasFlights = isRoundTrip
    ? (data.outbound_flights?.length || data.inbound_flights?.length)
    : data.flights?.length

  if (!hasFlights) return null

  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">✈️</span>
        <span className="tool-title">
          {data.origin} ↔ {data.destination} {isRoundTrip ? '왕복' : '편도'}
        </span>
        <span className="tool-meta">
          {data.departure_date} {isRoundTrip && data.return_date && `~ ${data.return_date}`} · {data.passengers}명
        </span>
      </div>

      {isRoundTrip ? (
        <>
          {data.outbound_flights && data.outbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">출발편 ({data.origin} → {data.destination})</div>
              <div className="flight-list">
                {data.outbound_flights.map((f, i) => (
                  <FlightItem key={`out-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}

          {data.inbound_flights && data.inbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">귀국편 ({data.destination} → {data.origin})</div>
              <div className="flight-list">
                {data.inbound_flights.map((f, i) => (
                  <FlightItem key={`in-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flight-list">
          {data.flights!.map((f, i) => (
            <FlightItem key={i} flight={f} />
          ))}
        </div>
      )}
    </div>
  )
}

function FlightItem({ flight }: { flight: Flight }) {
  return (
    <div className="flight-item">
      <div className="flight-airline">
        <span className="airline-name">{flight.airline}</span>
        <span className="flight-code">{flight.flight}</span>
        <span className="flight-class-badge">{flight.class}</span>
      </div>
      <div className="flight-route">
        <span className="flight-time">{flight.depart}</span>
        <span className="flight-arrow">
          <span className="flight-duration">{flight.duration}</span>
          <span className="flight-line">──────✈</span>
        </span>
        <span className="flight-time">{flight.arrive}</span>
      </div>
      <div className="flight-price">{flight.total_price.toLocaleString()}원</div>
    </div>
  )
}

// ── 여행 팁 카드 ──────────────────────────────
function TipsCard({ data }: { data: TravelTipsResult }) {
  if (data.status !== 'success') return null
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🗺️</span>
        <span className="tool-title">{data.destination} 여행 정보</span>
        <span className="tool-meta">{data.best_season}</span>
      </div>
      <p className="tips-overview">{data.overview}</p>
      <div className="tips-grid">
        {data.spots?.length && (
          <div className="tips-section">
            <div className="tips-section-title">📍 주요 관광지</div>
            <ul>{data.spots.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
        {data.food?.length && (
          <div className="tips-section">
            <div className="tips-section-title">🍜 추천 음식</div>
            <ul>{data.food.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {data.tips?.length && (
          <div className="tips-section">
            <div className="tips-section-title">💡 여행 팁</div>
            <ul>{data.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
        )}
      </div>
      <div className="tips-meta-row">
        <span>💱 {data.currency}</span>
        <span>🗣️ {data.language}</span>
      </div>
    </div>
  )
}
