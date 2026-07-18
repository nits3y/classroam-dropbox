import java.util.Scanner;

public class grade{

      public static void main (String[]args){
      Scanner input = new Scanner (System.in);
      
     int passed = 0, failed = 0;
     
     double Highest = 0, lowest = 100;
     double TotalAverage = 0;
     
     for (int i = 1; i<5; i++) {
     
     
     
     Systen.out.println("\nStudent" + i);
     Systen.out.println("Enter Student Name:");
         
     String name = input.nextLine();
     
     System.outprintln("Enter Midterm Grade:");
     
     double midterm = input.nexyDouble();
     
     Systen.out.println("Enter Final Grade");
     double finals = input.nextDouble();
     input.nextLine();
     
     double average = (midterm + finals) / 2;
     
     String remark;
     
     
     
     
     if (average>= 90){
   remark + "Excellent";  
   }
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     }      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      
      }
      
}
