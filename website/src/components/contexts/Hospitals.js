import React, { useContext } from 'react'
import { getDistance } from '../extra/funcs'
import SortContext from './Sort'
import SearchHospitalContext from './SearchHospital'
import SelectedFiltersContext from './SelectedFilters'

const HospitalsContext = React.createContext()

let HospitalsProvider = (props) => {
  
  const {sortValue} = useContext(SortContext)
  const {searchQuery} = useContext(SearchHospitalContext)
  const {filters} = useContext(SelectedFiltersContext)
  let { hospitals } = props

  hospitals = hospitals.map(hospital => {
    const localHospital = {...hospital.node}
    localHospital.distance = getDistance(localHospital.latitude, props.latitude, localHospital.longitude, props.longitude)
  
    return localHospital
  })

  //searching and filtering
  hospitals = hospitals.filter(hospital => {
    if (filters.length > 0) {
      return hospital.name.toLowerCase().includes(searchQuery.toLowerCase()) && filters.includes(hospital.category)  
    }

    return hospital.name.toLowerCase().includes(searchQuery.toLowerCase())
  })


  //sorting
  hospitals.sort((hospital, nextHospital) => {
    if (sortValue.descending) {
      return nextHospital[sortValue.field] - hospital[sortValue.field]
    }

    return hospital[sortValue.field] - nextHospital[sortValue.field]  
  })

  return (
    <HospitalsContext.Provider value={hospitals}>
      {props.children}
    </HospitalsContext.Provider>
  )

}

export { HospitalsProvider }
export default HospitalsContext
