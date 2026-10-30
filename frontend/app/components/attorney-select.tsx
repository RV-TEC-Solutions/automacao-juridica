import { Select } from "@/components/ui/select";

export function AttorneySelect(props: React.ComponentProps<typeof Select>) {
  return <Select name="attorney" aria-label="Por advogado" {...props}>
    <option value="">Todos os advogados</option>
    <option value="murilo">Dr. Murilo Mariz</option>
    <option value="cristiano">Dr. Cristiano Barros</option>
  </Select>;
}
